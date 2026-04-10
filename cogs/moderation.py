import logging
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone

from utils.authority import has_any_authority_role
from utils.channels import get_text_channel_by_name
from utils.paginator import EmbedPaginator, paginate_fields
from utils.roles import get_role_by_name
from utils import config
from utils.storage import (
    add_exile,
    add_warning,
    clear_member_warnings,
    clear_member_exile,
    get_active_exiles,
    get_member_exile,
    get_member_exile_history,
    get_member_warnings,
    remove_member_warning,
)

logger = logging.getLogger(__name__)

_MOD_RED = config.MODERATION_EMBED_COLOR
_SUCCESS = discord.Color.dark_green()


def parse_duration(duration_text: str) -> int:
    units = {"m": 60, "h": 3600, "d": 86400}
    if len(duration_text) < 2:
        raise ValueError("Duration must look like `10m`, `2h`, or `1d`.")
    unit = duration_text[-1].lower()
    value_text = duration_text[:-1]
    if unit not in units or not value_text.isdigit():
        raise ValueError("Duration must look like `10m`, `2h`, or `1d`.")
    value = int(value_text)
    if value <= 0:
        raise ValueError("Duration must be greater than zero.")
    return value * units[unit]


def format_duration(duration_seconds: int) -> str:
    days, remainder = divmod(duration_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts)


def _warning_field(entry: dict, guild: discord.Guild) -> tuple[str, str]:
    moderator = guild.get_member(int(entry["moderator_id"]))
    mod_display = moderator.mention if moderator else f"<@{entry['moderator_id']}>"
    ts = entry.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts)
        time_str = f"<t:{int(dt.timestamp())}:R>"
    except (ValueError, TypeError):
        time_str = ts or "Unknown"
    return (
        f"⚠️  Case #{entry['case_id']}",
        f"**📝 Reason:** {entry['reason']}\n**🛡️ By:** {mod_display}\n**🗓️ When:** {time_str}",
    )


def _exile_field(entry: dict, guild: discord.Guild) -> tuple[str, str]:
    moderator = guild.get_member(int(entry["moderator_id"]))
    mod_display = moderator.mention if moderator else f"<@{entry['moderator_id']}>"
    expires_at = int(float(entry["expires_at"]))
    resolution = entry.get("resolution") or "active"
    status_emoji = {
        "active": "🔴",
        "expired": "⏱️",
        "pardoned": "🕊️",
        "member-unavailable": "👻",
    }.get(resolution, "❓")
    return (
        f"⛓️  Case #{entry['case_id']}",
        (
            f"**📝 Reason:** {entry['reason']}\n"
            f"**⏳ Duration:** {format_duration(int(entry['duration_seconds']))}\n"
            f"**🛡️ By:** {mod_display}\n"
            f"**🕐 Ended:** <t:{expires_at}:F>\n"
            f"**{status_emoji} Status:** {resolution.capitalize()}"
        ),
    )


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.exile_release_task.start()

    def cog_unload(self) -> None:
        self.exile_release_task.cancel()

    async def ensure_moderation_authority(self, ctx: commands.Context) -> bool:
        if not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return False
        if has_any_authority_role(ctx.author, config.MODERATION_ALLOWED_ROLES):
            return True
        embed = discord.Embed(
            title="🚫 Access Denied",
            description="Moderation commands are reserved for authority members.",
            color=discord.Color.red(),
        )
        embed.add_field(
            name="🛡️ Required Rank",
            value="\n".join(f"• {r}" for r in config.MODERATION_ALLOWED_ROLES),
            inline=False,
        )
        await ctx.send(embed=embed)
        return False

    async def send_log_embed(self, guild: discord.Guild, embed: discord.Embed) -> None:
        logs_channel = get_text_channel_by_name(guild, config.SERVER_LOGS_CHANNEL)
        if logs_channel is None:
            return
        try:
            await logs_channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning("Cannot post to server-logs in guild %s — missing permissions.", guild.id)

    async def release_expired_exiles(self) -> None:
        now_timestamp = datetime.now(timezone.utc).timestamp()
        for guild_id, members in get_active_exiles().items():
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                continue
            quarantine_role = get_role_by_name(guild, config.QUARANTINE_ROLE)
            if quarantine_role is None:
                continue
            for member_id, exile in list(members.items()):
                if float(exile["expires_at"]) > now_timestamp:
                    continue
                member = guild.get_member(int(member_id))
                if member is None:
                    clear_member_exile(guild.id, int(member_id), resolution="member-unavailable")
                    continue
                if quarantine_role in member.roles:
                    try:
                        await member.remove_roles(quarantine_role, reason="Timed exile expired.")
                    except discord.Forbidden:
                        logger.warning(
                            "Cannot remove Quarantine from %s in guild %s — missing Manage Roles.",
                            member_id, guild_id,
                        )
                        continue
                log_embed = discord.Embed(
                    title="⏱️ Timed Exile Expired",
                    description=f"{member.mention} has been automatically released from quarantine.",
                    color=_SUCCESS,
                )
                log_embed.add_field(name="👤 Member", value=member.mention, inline=True)
                log_embed.add_field(name="📝 Original Reason", value=str(exile["reason"]), inline=False)
                log_embed.set_footer(text="L'Mkhzen · Auto-Release System")
                await self.send_log_embed(guild, log_embed)
                clear_member_exile(guild.id, member.id, resolution="expired")
                logger.info("Auto-released exile for member=%s in guild=%s.", member.id, guild.id)

    @tasks.loop(seconds=30)
    async def exile_release_task(self) -> None:
        await self.release_expired_exiles()

    @exile_release_task.before_loop
    async def before_exile_release_task(self) -> None:
        await self.bot.wait_until_ready()

    # ─── WARN ────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="warn", description="Issue and record a formal warning.")
    @app_commands.describe(member="The member to warn.", reason="The reason for the warning.")
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided.") -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        logger.info("MODERATION | guild=%s | mod=%s | cmd=warn | target=%s", ctx.guild.id, ctx.author.id, member.id)

        entry = add_warning(guild_id=ctx.guild.id, member_id=member.id, moderator_id=ctx.author.id, reason=reason)
        total_warnings = len(get_member_warnings(ctx.guild.id, member.id))

        embed = discord.Embed(
            title="⚠️ Formal Warning Issued",
            color=_MOD_RED,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🆔 Case", value=f"**#{entry['case_id']}**", inline=True)
        embed.add_field(name="📊 Total Warnings", value=str(total_warnings), inline=True)
        embed.add_field(name="👤 Member", value=member.mention, inline=False)
        embed.add_field(name="🛡️ Issued By", value=ctx.author.mention, inline=True)
        embed.add_field(name="📝 Reason", value=entry["reason"], inline=False)
        embed.set_footer(text=f"Medina Hub · Moderation Registry  ·  {ctx.guild.name}")
        await ctx.send(embed=embed)

        log_embed = embed.copy()
        log_embed.title = "⚠️ Warning Logged"
        await self.send_log_embed(ctx.guild, log_embed)

    # ─── WARNINGS ────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="warnings", description="Show warning history for a member.")
    @app_commands.describe(member="The member whose warnings you want to view.")
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def warnings(self, ctx: commands.Context, member: discord.Member) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        entries = get_member_warnings(ctx.guild.id, member.id)
        if not entries:
            embed = discord.Embed(
                title="📋 Warning Dossier",
                description=f"{member.mention} has a **clean record** — no warnings on file.",
                color=_SUCCESS,
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)
            return

        guild = ctx.guild

        def build_field(entry: dict) -> tuple[str, str]:
            return _warning_field(entry, guild)

        pages = paginate_fields(
            entries=entries,
            build_field=build_field,
            title="📋 Warning Dossier",
            description=f"Recorded warnings for {member.mention}",
            color=discord.Color(_MOD_RED),
            footer_base="Medina Hub · Moderation Registry",
            thumbnail_url=member.display_avatar.url,
        )

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            await ctx.send(embed=pages[0], view=EmbedPaginator(pages))

    # ─── UNWARN ──────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="unwarn", description="Remove a specific warning case from a member.")
    @app_commands.describe(member="The member whose warning you want to remove.", case_id="The case number to remove.")
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def unwarn(self, ctx: commands.Context, member: discord.Member, case_id: int) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        logger.info("MODERATION | guild=%s | mod=%s | cmd=unwarn | target=%s | case=%s", ctx.guild.id, ctx.author.id, member.id, case_id)

        removed = remove_member_warning(ctx.guild.id, member.id, case_id)
        if removed is None:
            embed = discord.Embed(
                title="❌ Case Not Found",
                description=f"No warning case **#{case_id}** exists for {member.mention}.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return

        remaining = len(get_member_warnings(ctx.guild.id, member.id))

        embed = discord.Embed(
            title="✅ Warning Expunged",
            description=f"Case **#{case_id}** has been removed from {member.mention}'s record.",
            color=_SUCCESS,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Member", value=member.mention, inline=True)
        embed.add_field(name="📊 Remaining Warnings", value=str(remaining), inline=True)
        embed.add_field(name="🛡️ Removed By", value=ctx.author.mention, inline=False)
        embed.add_field(name="📝 Original Reason", value=str(removed["reason"]), inline=False)
        embed.set_footer(text="Medina Hub · Moderation Registry")
        await ctx.send(embed=embed)
        await self.send_log_embed(ctx.guild, embed.copy())

    # ─── CLEARWARNINGS ───────────────────────────────────────────────────────

    @commands.hybrid_command(name="clearwarnings", description="Remove all warnings recorded for a member.")
    @app_commands.describe(member="The member whose warnings you want to clear.")
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def clearwarnings(self, ctx: commands.Context, member: discord.Member) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        logger.info("MODERATION | guild=%s | mod=%s | cmd=clearwarnings | target=%s", ctx.guild.id, ctx.author.id, member.id)

        removed_count = clear_member_warnings(ctx.guild.id, member.id)
        if removed_count == 0:
            embed = discord.Embed(
                title="📋 Nothing to Clear",
                description=f"{member.mention} has no recorded warnings.",
                color=discord.Color.greyple(),
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="🧹 Record Purged",
            description=f"All warnings have been cleared for {member.mention}.",
            color=_SUCCESS,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Member", value=member.mention, inline=True)
        embed.add_field(name="🗑️ Cases Removed", value=f"**{removed_count}**", inline=True)
        embed.add_field(name="🛡️ Cleared By", value=ctx.author.mention, inline=False)
        embed.set_footer(text="Medina Hub · Moderation Registry")
        await ctx.send(embed=embed)
        await self.send_log_embed(ctx.guild, embed.copy())

    # ─── EXILE ───────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="exile", description="Place a member in timed quarantine.")
    @app_commands.describe(
        member="The member to exile.",
        duration="Exile duration: 10m, 2h, or 1d.",
        reason="The reason for the exile.",
    )
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def exile(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: str,
        *,
        reason: str = "Pending review.",
    ) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        quarantine_role = get_role_by_name(ctx.guild, config.QUARANTINE_ROLE)
        if quarantine_role is None:
            await ctx.send(f'The role `{config.QUARANTINE_ROLE}` does not exist. Create it before using this command.')
            return

        if quarantine_role in member.roles:
            embed = discord.Embed(
                title="⛓️ Already in Quarantine",
                description=f"{member.mention} is already under quarantine.",
                color=discord.Color.orange(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)
            return

        try:
            duration_seconds = parse_duration(duration)
        except ValueError as error:
            embed = discord.Embed(title="❌ Invalid Duration", description=str(error), color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        logger.info("MODERATION | guild=%s | mod=%s | cmd=exile | target=%s | duration=%ss", ctx.guild.id, ctx.author.id, member.id, duration_seconds)

        await member.add_roles(quarantine_role, reason=f"Exiled by {ctx.author} | {reason}")
        exile_entry = add_exile(
            guild_id=ctx.guild.id,
            member_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            duration_seconds=duration_seconds,
        )
        expires_ts = int(exile_entry["expires_at"])

        embed = discord.Embed(
            title="⛓️ Exile Decreed",
            description=f"{member.mention} has been moved into quarantine.",
            color=_MOD_RED,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🆔 Case", value=f"**#{exile_entry['case_id']}**", inline=True)
        embed.add_field(name="⏳ Duration", value=f"**{format_duration(duration_seconds)}**", inline=True)
        embed.add_field(name="🕐 Expires", value=f"<t:{expires_ts}:R>  (<t:{expires_ts}:f>)", inline=False)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text="Medina Hub · Exile Registry")
        await ctx.send(embed=embed)

        log_embed = discord.Embed(
            title="⛓️ Exile Logged",
            description=f"{member.mention} placed under quarantine.",
            color=_MOD_RED,
        )
        log_embed.set_thumbnail(url=member.display_avatar.url)
        log_embed.add_field(name="👤 Member", value=member.mention, inline=True)
        log_embed.add_field(name="🛡️ Issued By", value=ctx.author.mention, inline=True)
        log_embed.add_field(name="⏳ Duration", value=format_duration(duration_seconds), inline=True)
        log_embed.add_field(name="🕐 Expires", value=f"<t:{expires_ts}:F>", inline=False)
        log_embed.add_field(name="📝 Reason", value=reason, inline=False)
        log_embed.set_footer(text="Medina Hub · Exile Registry")
        await self.send_log_embed(ctx.guild, log_embed)

    # ─── EXILES ──────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="exiles", description="Show exile history for a member.")
    @app_commands.describe(member="The member whose exile history you want to inspect.")
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def exiles(self, ctx: commands.Context, member: discord.Member) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        entries = get_member_exile_history(ctx.guild.id, member.id)
        if not entries:
            embed = discord.Embed(
                title="📜 Exile Codex",
                description=f"{member.mention} has **no exile history** on record.",
                color=_SUCCESS,
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)
            return

        guild = ctx.guild

        def build_field(entry: dict) -> tuple[str, str]:
            return _exile_field(entry, guild)

        pages = paginate_fields(
            entries=entries,
            build_field=build_field,
            title="📜 Exile Codex",
            description=f"Exile history for {member.mention}",
            color=discord.Color(_MOD_RED),
            footer_base="Medina Hub · Exile Registry",
            thumbnail_url=member.display_avatar.url,
        )

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            await ctx.send(embed=pages[0], view=EmbedPaginator(pages))

    # ─── TIMELEFT ────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="timeleft", description="Show the remaining time on a member's exile.")
    @app_commands.describe(member="The member whose exile timer you want to inspect.")
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def timeleft(self, ctx: commands.Context, member: discord.Member) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        exile_entry = get_member_exile(ctx.guild.id, member.id)
        if exile_entry is None:
            embed = discord.Embed(
                title="✅ Not Under Exile",
                description=f"{member.mention} does not have an active timed exile.",
                color=_SUCCESS,
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)
            return

        expires_ts = int(float(exile_entry["expires_at"]))
        embed = discord.Embed(
            title="⏳ Countdown Active",
            description=f"Timed exile status for {member.mention}",
            color=_MOD_RED,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="⌛ Time Remaining", value=f"<t:{expires_ts}:R>", inline=True)
        embed.add_field(name="🕐 Ends At", value=f"<t:{expires_ts}:F>", inline=True)
        embed.add_field(name="📝 Reason", value=str(exile_entry["reason"]), inline=False)
        embed.set_footer(text="Medina Hub · Exile Registry")
        await ctx.send(embed=embed)

    # ─── PARDON ──────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="pardon", description="Remove quarantine from a member.")
    @app_commands.describe(member="The member to pardon.")
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pardon(self, ctx: commands.Context, member: discord.Member) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        quarantine_role = get_role_by_name(ctx.guild, config.QUARANTINE_ROLE)
        if quarantine_role is None:
            await ctx.send(f'The role `{config.QUARANTINE_ROLE}` does not exist.')
            return

        if quarantine_role not in member.roles:
            embed = discord.Embed(
                title="✅ Not in Quarantine",
                description=f"{member.mention} is not currently under quarantine.",
                color=discord.Color.greyple(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await ctx.send(embed=embed)
            return

        logger.info("MODERATION | guild=%s | mod=%s | cmd=pardon | target=%s", ctx.guild.id, ctx.author.id, member.id)

        await member.remove_roles(quarantine_role, reason=f"Pardoned by {ctx.author}")
        clear_member_exile(ctx.guild.id, member.id, resolution="pardoned")

        embed = discord.Embed(
            title="🕊️ Pardon Granted",
            description=f"{member.mention} has been released from quarantine.",
            color=_SUCCESS,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Member", value=member.mention, inline=True)
        embed.add_field(name="🛡️ Issued By", value=ctx.author.mention, inline=True)
        embed.set_footer(text="Medina Hub · Exile Registry")
        await ctx.send(embed=embed)

        log_embed = embed.copy()
        log_embed.title = "🕊️ Pardon Logged"
        await self.send_log_embed(ctx.guild, log_embed)

    # ─── ERROR HANDLER ───────────────────────────────────────────────────────

    @warn.error
    @warnings.error
    @unwarn.error
    @clearwarnings.error
    @exile.error
    @exiles.error
    @timeleft.error
    @pardon.error
    async def moderation_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        original_error = getattr(error, "original", error)

        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏱️ Slow Down",
                description=f"This command is on cooldown. Try again in **{error.retry_after:.1f}s**.",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        if isinstance(error, commands.MissingRequiredArgument):
            if ctx.command and ctx.command.name == "exile":
                await ctx.send("Missing command data. Example: `/exile @user 30m spam`.")
            else:
                await ctx.send("You must mention a member to use this command.")
            return

        if isinstance(error, commands.MemberNotFound):
            await ctx.send("I could not find that member in this server.")
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command.")
            return

        if isinstance(original_error, discord.Forbidden):
            await ctx.send(
                "Discord denied this action. Make sure L'Mkhzen has `Manage Roles` and that the bot role is above "
                "`Quarantine` and above the target member's highest role."
            )
            return

        raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
