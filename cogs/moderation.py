import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone

from utils.authority import has_any_authority_role
from utils.channels import get_text_channel_by_name
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


def get_role_by_name(guild: discord.Guild, role_name: str) -> discord.Role | None:
    return discord.utils.get(guild.roles, name=role_name)


def parse_duration(duration_text: str) -> int:
    units = {
        "m": 60,
        "h": 3600,
        "d": 86400,
    }
    if len(duration_text) < 2:
        raise ValueError("Duration must look like 10m, 2h, or 1d.")

    unit = duration_text[-1].lower()
    value_text = duration_text[:-1]
    if unit not in units or not value_text.isdigit():
        raise ValueError("Duration must look like 10m, 2h, or 1d.")

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

        allowed_roles = ", ".join(config.MODERATION_ALLOWED_ROLES)
        await ctx.send(f"Authority denied. Moderation commands are reserved for: {allowed_roles}.")
        return False

    async def send_log_embed(self, guild: discord.Guild, embed: discord.Embed) -> None:
        logs_channel = get_text_channel_by_name(guild, config.SERVER_LOGS_CHANNEL)
        if logs_channel is None:
            return

        try:
            await logs_channel.send(embed=embed)
        except discord.Forbidden:
            return

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
                        continue

                log_embed = discord.Embed(
                    title="Timed Exile Expired",
                    description=f"{member.mention} has been released automatically.",
                    color=discord.Color.dark_green(),
                )
                log_embed.add_field(name="Member", value=member.mention, inline=False)
                log_embed.add_field(name="Original Reason", value=str(exile["reason"]), inline=False)
                log_embed.add_field(name="Started", value=str(exile["started_at"]), inline=False)
                await self.send_log_embed(guild, log_embed)
                clear_member_exile(guild.id, member.id, resolution="expired")

    @tasks.loop(seconds=30)
    async def exile_release_task(self) -> None:
        await self.release_expired_exiles()

    @exile_release_task.before_loop
    async def before_exile_release_task(self) -> None:
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="warn", description="Issue and record a formal warning.")
    @app_commands.describe(member="The member to warn.", reason="The reason for the warning.")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided.") -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        warning_entry = add_warning(
            guild_id=ctx.guild.id,
            member_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
        )

        embed = discord.Embed(
            title="Formal Warning",
            color=config.MODERATION_EMBED_COLOR,
        )
        embed.add_field(name="Case", value=f"#{warning_entry['case_id']}", inline=False)
        embed.add_field(name="Member", value=member.mention, inline=False)
        embed.add_field(name="Issued By", value=ctx.author.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)

        await ctx.send(embed=embed)
        await self.send_log_embed(ctx.guild, embed.copy())

    @commands.hybrid_command(name="warnings", description="Show warning history for a member.")
    @app_commands.describe(member="The member whose warnings you want to view.")
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx: commands.Context, member: discord.Member) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        warning_entries = get_member_warnings(ctx.guild.id, member.id)
        if not warning_entries:
            await ctx.send(f"{member.mention} has no recorded warnings.")
            return

        embed = discord.Embed(
            title="Warning History",
            description=f"Recorded warnings for {member.mention}",
            color=config.MODERATION_EMBED_COLOR,
        )

        for entry in warning_entries[-5:]:
            moderator = ctx.guild.get_member(int(entry["moderator_id"]))
            moderator_display = moderator.mention if moderator else f"<@{entry['moderator_id']}>"
            embed.add_field(
                name=f"Case #{entry['case_id']}",
                value=(
                    f"**Moderator:** {moderator_display}\n"
                    f"**Reason:** {entry['reason']}\n"
                    f"**Timestamp:** {entry['timestamp']}"
                ),
                inline=False,
            )

        if len(warning_entries) > 5:
            embed.set_footer(text=f"Showing latest 5 of {len(warning_entries)} warnings.")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="unwarn", description="Remove a specific warning case from a member.")
    @app_commands.describe(member="The member whose warning you want to remove.", case_id="The case number to remove.")
    @commands.has_permissions(manage_messages=True)
    async def unwarn(self, ctx: commands.Context, member: discord.Member, case_id: int) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        removed_warning = remove_member_warning(ctx.guild.id, member.id, case_id)
        if removed_warning is None:
            await ctx.send(f"No warning case `#{case_id}` was found for {member.mention}.")
            return

        embed = discord.Embed(
            title="Warning Removed",
            description=f"Case `#{case_id}` has been removed for {member.mention}.",
            color=discord.Color.dark_green(),
        )
        embed.add_field(name="Member", value=member.mention, inline=False)
        embed.add_field(name="Removed By", value=ctx.author.mention, inline=False)
        embed.add_field(name="Original Reason", value=str(removed_warning["reason"]), inline=False)
        await ctx.send(embed=embed)
        await self.send_log_embed(ctx.guild, embed.copy())

    @commands.hybrid_command(name="clearwarnings", description="Remove all warnings recorded for a member.")
    @app_commands.describe(member="The member whose warnings you want to clear.")
    @commands.has_permissions(manage_messages=True)
    async def clearwarnings(self, ctx: commands.Context, member: discord.Member) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        removed_count = clear_member_warnings(ctx.guild.id, member.id)
        if removed_count == 0:
            await ctx.send(f"{member.mention} has no recorded warnings to clear.")
            return

        embed = discord.Embed(
            title="Warnings Cleared",
            description=f"All warnings have been cleared for {member.mention}.",
            color=discord.Color.dark_green(),
        )
        embed.add_field(name="Member", value=member.mention, inline=False)
        embed.add_field(name="Cleared By", value=ctx.author.mention, inline=False)
        embed.add_field(name="Removed Cases", value=str(removed_count), inline=False)
        await ctx.send(embed=embed)
        await self.send_log_embed(ctx.guild, embed.copy())

    @commands.hybrid_command(name="exile", description="Place a member in timed quarantine.")
    @app_commands.describe(
        member="The member to exile.",
        duration="Exile duration such as 10m, 2h, or 1d.",
        reason="The reason for the exile.",
    )
    @commands.has_permissions(manage_roles=True)
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
            await ctx.send(
                f'The role "{config.QUARANTINE_ROLE}" does not exist yet. Create it before using this command.'
            )
            return

        if quarantine_role in member.roles:
            await ctx.send(f"{member.mention} is already under quarantine.")
            return

        try:
            duration_seconds = parse_duration(duration)
        except ValueError as error:
            await ctx.send(str(error))
            return

        await member.add_roles(quarantine_role, reason=f"Exiled by {ctx.author} | {reason}")
        exile_entry = add_exile(
            guild_id=ctx.guild.id,
            member_id=member.id,
            moderator_id=ctx.author.id,
            reason=reason,
            duration_seconds=duration_seconds,
        )

        embed = discord.Embed(
            title="Exile Enforced",
            description=f"{member.mention} has been moved under quarantine.",
            color=config.MODERATION_EMBED_COLOR,
        )
        embed.add_field(name="Duration", value=format_duration(duration_seconds), inline=False)
        embed.add_field(name="Expires", value=f"<t:{int(exile_entry['expires_at'])}:R>", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)

        log_embed = discord.Embed(
            title="Exile Enforced",
            description=f"{member.mention} has been moved under quarantine.",
            color=config.MODERATION_EMBED_COLOR,
        )
        log_embed.add_field(name="Member", value=member.mention, inline=False)
        log_embed.add_field(name="Issued By", value=ctx.author.mention, inline=False)
        log_embed.add_field(name="Duration", value=format_duration(duration_seconds), inline=False)
        log_embed.add_field(name="Expires", value=f"<t:{int(exile_entry['expires_at'])}:F>", inline=False)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        await self.send_log_embed(ctx.guild, log_embed)

    @commands.hybrid_command(name="exiles", description="Show exile history for a member.")
    @app_commands.describe(member="The member whose exile history you want to inspect.")
    @commands.has_permissions(manage_roles=True)
    async def exiles(self, ctx: commands.Context, member: discord.Member) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        exile_entries = get_member_exile_history(ctx.guild.id, member.id)
        if not exile_entries:
            await ctx.send(f"{member.mention} has no exile history.")
            return

        embed = discord.Embed(
            title="Exile History",
            description=f"Recorded exile actions for {member.mention}",
            color=config.MODERATION_EMBED_COLOR,
        )

        for entry in exile_entries[-5:]:
            moderator = ctx.guild.get_member(int(entry["moderator_id"]))
            moderator_display = moderator.mention if moderator else f"<@{entry['moderator_id']}>"
            expires_at = int(float(entry["expires_at"]))
            resolution = entry.get("resolution") or "active"
            embed.add_field(
                name=f"Case #{entry['case_id']}",
                value=(
                    f"**Moderator:** {moderator_display}\n"
                    f"**Duration:** {format_duration(int(entry['duration_seconds']))}\n"
                    f"**Reason:** {entry['reason']}\n"
                    f"**Ends:** <t:{expires_at}:F>\n"
                    f"**Resolution:** {resolution}"
                ),
                inline=False,
            )

        if len(exile_entries) > 5:
            embed.set_footer(text=f"Showing latest 5 of {len(exile_entries)} exile records.")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="timeleft", description="Show the remaining time on a member's exile.")
    @app_commands.describe(member="The member whose exile timer you want to inspect.")
    @commands.has_permissions(manage_roles=True)
    async def timeleft(self, ctx: commands.Context, member: discord.Member) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        exile_entry = get_member_exile(ctx.guild.id, member.id)
        if exile_entry is None:
            await ctx.send(f"{member.mention} does not have an active timed exile.")
            return

        expires_at = int(float(exile_entry["expires_at"]))
        embed = discord.Embed(
            title="Exile Countdown",
            description=f"Timed exile status for {member.mention}",
            color=config.MODERATION_EMBED_COLOR,
        )
        embed.add_field(name="Time Remaining", value=f"<t:{expires_at}:R>", inline=False)
        embed.add_field(name="Ends At", value=f"<t:{expires_at}:F>", inline=False)
        embed.add_field(name="Reason", value=str(exile_entry["reason"]), inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="pardon", description="Remove quarantine from a member.")
    @app_commands.describe(member="The member to pardon.")
    @commands.has_permissions(manage_roles=True)
    async def pardon(self, ctx: commands.Context, member: discord.Member) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return
        if not await self.ensure_moderation_authority(ctx):
            return

        quarantine_role = get_role_by_name(ctx.guild, config.QUARANTINE_ROLE)
        if quarantine_role is None:
            await ctx.send(f'The role "{config.QUARANTINE_ROLE}" does not exist yet.')
            return

        if quarantine_role not in member.roles:
            await ctx.send(f"{member.mention} is not currently under quarantine.")
            return

        await member.remove_roles(quarantine_role, reason=f"Pardoned by {ctx.author}")
        clear_member_exile(ctx.guild.id, member.id, resolution="pardoned")

        embed = discord.Embed(
            title="Pardon Granted",
            description=f"{member.mention} has been released from quarantine.",
            color=discord.Color.dark_green(),
        )
        await ctx.send(embed=embed)

        log_embed = discord.Embed(
            title="Pardon Granted",
            description=f"{member.mention} has been released from quarantine.",
            color=discord.Color.dark_green(),
        )
        log_embed.add_field(name="Member", value=member.mention, inline=False)
        log_embed.add_field(name="Issued By", value=ctx.author.mention, inline=False)
        await self.send_log_embed(ctx.guild, log_embed)

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

        if isinstance(error, commands.MissingRequiredArgument):
            if ctx.command and ctx.command.name == "exile":
                await ctx.send("Missing command data. Example: `/exile @user 30m spam`.")
                return

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
