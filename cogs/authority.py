import discord
from discord import app_commands
from discord.ext import commands

from utils import config
from utils.authority import has_any_authority_role, resolve_rank
from utils.channels import get_text_channel_by_name
from utils.paginator import EmbedPaginator
from utils.storage import get_member_exile, get_member_warnings

_TIER_BADGES = ["👑", "🥇", "🥈", "🥉", "🏅", "🎖️", "⚜️", "📜", "🌿", "⛺"]
_WARN_AMBER = 0xE67E22


class Authority(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ─── RANK ────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="rank", description="Show a member's authority rank.")
    @app_commands.describe(member="The member to inspect. Leave empty to inspect yourself.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rank(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        target = member or ctx.author
        if not isinstance(target, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return

        current_rank = resolve_rank(target)
        try:
            tier_index = config.AUTHORITY_HIERARCHY.index(current_rank)
            badge = _TIER_BADGES[tier_index] if tier_index < len(_TIER_BADGES) else "🔘"
            tier_label = f"Tier {tier_index + 1}"
        except ValueError:
            badge = "❔"
            tier_label = "Unranked"

        embed = discord.Embed(
            title=f"{badge} Authority Standing",
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="👤 Member", value=target.mention, inline=True)
        embed.add_field(name="📍 Position", value=tier_label, inline=True)
        embed.add_field(name="🏅 Rank", value=current_rank, inline=False)
        embed.set_footer(text=f"{config.SERVER_NAME} · Authority Registry")
        await ctx.send(embed=embed)

    # ─── HIERARCHY ───────────────────────────────────────────────────────────

    @commands.hybrid_command(name="hierarchy", description="Display the full authority ladder.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def hierarchy(self, ctx: commands.Context) -> None:
        per_page = 5
        roles = config.AUTHORITY_HIERARCHY
        chunks = [roles[i:i + per_page] for i in range(0, len(roles), per_page)]
        pages: list[discord.Embed] = []

        for page_num, chunk in enumerate(chunks, start=1):
            embed = discord.Embed(
                title="👑 Medina Hierarchy",
                description=f"The recognized order of authority within **{config.SERVER_NAME}**",
                color=discord.Color.gold(),
            )
            if ctx.guild and ctx.guild.icon:
                embed.set_thumbnail(url=ctx.guild.icon.url)

            lines: list[str] = []
            for role_name in chunk:
                global_index = roles.index(role_name)
                badge = _TIER_BADGES[global_index] if global_index < len(_TIER_BADGES) else "🔘"
                lines.append(f"{badge}  **{global_index + 1}.** {role_name}")

            embed.add_field(name="⚖️ Rank Ladder", value="\n".join(lines), inline=False)
            page_label = f"Page {page_num} of {len(chunks)}  ·  {len(roles)} total ranks"
            embed.set_footer(text=f"{config.SERVER_NAME} · Highest authority appears first  ·  {page_label}")
            pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            await ctx.send(embed=pages[0], view=EmbedPaginator(pages))

    # ─── AUDIT ───────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="audit", description="Show a full audit profile for a member.")
    @app_commands.describe(member="The member to audit. Leave empty to audit yourself.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def audit(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return

        target = member or ctx.author
        if not isinstance(target, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return

        current_rank = resolve_rank(target)
        warning_entries = get_member_warnings(ctx.guild.id, target.id)
        exile_entry = get_member_exile(ctx.guild.id, target.id)
        visible_roles = [role.mention for role in reversed(target.roles) if role.name != "@everyone"]
        role_display = " · ".join(visible_roles) if visible_roles else "*No visible roles.*"

        warn_count = len(warning_entries)
        has_exile = exile_entry is not None

        if has_exile and warn_count > 0:
            status_badge = "☠️  Exiled & Warned"
            status_color = discord.Color.dark_red()
        elif has_exile:
            status_badge = "⛓️  Under Exile"
            status_color = discord.Color.orange()
        elif warn_count > 0:
            status_badge = "⚠️  Has Warnings"
            status_color = discord.Color(_WARN_AMBER)
        else:
            status_badge = "✅  Standing Clear"
            status_color = discord.Color.dark_teal()

        embed = discord.Embed(
            title="🔍 Authority Dossier",
            description=f"System profile for {target.mention}",
            color=status_color,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🏅 Hierarchy", value=current_rank, inline=True)
        embed.add_field(name="📊 Status", value=status_badge, inline=True)
        embed.add_field(name="⚠️ Warnings", value=str(warn_count), inline=True)
        embed.add_field(name="🎖️ Roles", value=role_display, inline=False)

        if exile_entry:
            expires_ts = int(float(exile_entry["expires_at"]))
            embed.add_field(name="⛓️ Exile Ends", value=f"<t:{expires_ts}:R>  (<t:{expires_ts}:f>)", inline=False)
            embed.add_field(name="📝 Exile Reason", value=str(exile_entry["reason"]), inline=False)

        if warning_entries:
            latest = warning_entries[-1]
            moderator = ctx.guild.get_member(int(latest["moderator_id"]))
            mod_display = moderator.mention if moderator else f"<@{latest['moderator_id']}>"
            embed.add_field(
                name="🕵️ Latest Warning",
                value=(
                    f"**Case #{latest['case_id']}** · By {mod_display}\n"
                    f"*{latest['reason']}*"
                ),
                inline=False,
            )

        embed.set_footer(text=f"{config.SERVER_NAME} · Audit Registry")
        await ctx.send(embed=embed)

    # ─── ANNOUNCE ────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="announce", description="Send an authority announcement to the announcements channel.")
    @app_commands.describe(message="The authority message to publish.")
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def announce(self, ctx: commands.Context, *, message: str) -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return

        if not has_any_authority_role(ctx.author, config.ANNOUNCE_ALLOWED_ROLES):
            embed = discord.Embed(
                title="🚫 Access Denied",
                description="Official decrees are reserved for senior authority members.",
                color=discord.Color.red(),
            )
            embed.add_field(
                name="👑 Required Rank",
                value="\n".join(f"• {r}" for r in config.ANNOUNCE_ALLOWED_ROLES),
                inline=False,
            )
            await ctx.send(embed=embed)
            return

        announcements_channel = get_text_channel_by_name(ctx.guild, config.ANNOUNCEMENTS_CHANNEL)
        if announcements_channel is None:
            await ctx.send(f'Authority channel not found. Create or rename the channel to `{config.ANNOUNCEMENTS_CHANNEL}`.')
            return

        embed = discord.Embed(
            title="📣 Official Decree",
            description=message,
            color=config.ANNOUNCE_EMBED_COLOR,
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.add_field(name="🛡️ Issued By", value=ctx.author.mention, inline=True)
        embed.set_footer(text=f"{config.SERVER_NAME} · L'Mkhzen Authority System")

        try:
            await announcements_channel.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("Authority denied by Discord. Make sure L'Mkhzen can send messages in the announcements channel.")
            return

        confirm = discord.Embed(
            title="✅ Decree Delivered",
            description=f"Your announcement was posted to {announcements_channel.mention}.",
            color=discord.Color.dark_green(),
        )
        await ctx.send(embed=confirm)

    # ─── ERROR HANDLER ───────────────────────────────────────────────────────

    @rank.error
    @hierarchy.error
    @audit.error
    @announce.error
    async def authority_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏱️ Slow Down",
                description=f"This command is on cooldown. Try again in **{error.retry_after:.1f}s**.",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        if isinstance(error, commands.MemberNotFound):
            await ctx.send("I could not find that member in this server.")
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You must provide a message for the announcement.")
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not meet the Discord permission requirement to issue authority announcements.")
            return

        original_error = getattr(error, "original", error)
        if isinstance(original_error, discord.Forbidden):
            await ctx.send("Discord denied access to the announcements channel.")
            return

        raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Authority(bot))
