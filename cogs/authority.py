import logging
import discord
from discord import app_commands
from discord.ext import commands

from utils import config
from utils.authority import has_any_authority_role, resolve_rank
from utils.channels import get_text_channel_by_name
from utils.paginator import EmbedPaginator
from utils.prestige import get_member_prestige, reset_prestige_partial
from utils.roles import get_role_by_name
from utils.storage import get_member_exile, get_member_warnings

logger = logging.getLogger(__name__)

_TIER_BADGES = ["👑", "🥇", "🥈", "🥉", "🏅", "🎖️", "⚜️", "📜", "🌿", "⛺"]
_WARN_AMBER = 0xE67E22


class Authority(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ─── RANK ────────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="rank", description="Show a member's authority rank.")
    @app_commands.describe(member="The member to inspect. Leave empty for yourself.")
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
            badge, tier_label = "❔", "Unranked"

        embed = discord.Embed(title=f"{badge} Authority Standing", color=discord.Color.gold())
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
        roles = config.AUTHORITY_HIERARCHY
        chunks = [roles[i:i + 5] for i in range(0, len(roles), 5)]
        pages: list[discord.Embed] = []
        for page_num, chunk in enumerate(chunks, 1):
            embed = discord.Embed(
                title="👑 Medina Hierarchy",
                description=f"The recognized order of authority within **{config.SERVER_NAME}**",
                color=discord.Color.gold(),
            )
            if ctx.guild and ctx.guild.icon:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            lines: list[str] = []
            for role_name in chunk:
                gi = roles.index(role_name)
                badge = _TIER_BADGES[gi] if gi < len(_TIER_BADGES) else "🔘"
                lines.append(f"{badge}  **{gi + 1}.** {role_name}")
            embed.add_field(name="⚖️ Rank Ladder", value="\n".join(lines), inline=False)
            embed.set_footer(text=f"{config.SERVER_NAME} · Page {page_num} of {len(chunks)}  ·  Highest appears first")
            pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            await ctx.send(embed=pages[0], view=EmbedPaginator(pages))

    # ─── AUDIT ───────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="audit", description="Show a full audit profile for a member.")
    @app_commands.describe(member="The member to audit. Leave empty for yourself.")
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
        prestige_data = get_member_prestige(ctx.guild.id, target.id)
        prestige_score = prestige_data.get("prestige", 0)
        visible_roles = [role.mention for role in reversed(target.roles) if role.name != "@everyone"]
        role_display = " · ".join(visible_roles) if visible_roles else "*No visible roles.*"

        warn_count = len(warning_entries)
        has_exile = exile_entry is not None

        if has_exile and warn_count > 0:
            status_badge, status_color = "☠️  Exiled & Warned", discord.Color.dark_red()
        elif has_exile:
            status_badge, status_color = "⛓️  Under Exile", discord.Color.orange()
        elif warn_count > 0:
            status_badge, status_color = "⚠️  Has Warnings", discord.Color(_WARN_AMBER)
        else:
            status_badge, status_color = "✅  Standing Clear", discord.Color.dark_teal()

        embed = discord.Embed(title="🔍 Authority Dossier", description=f"System profile for {target.mention}", color=status_color)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🏅 Hierarchy", value=current_rank, inline=True)
        embed.add_field(name="📊 Status", value=status_badge, inline=True)
        embed.add_field(name="⭐ Prestige", value=f"{prestige_score:,}", inline=True)
        embed.add_field(name="⚠️ Warnings", value=str(warn_count), inline=True)
        embed.add_field(name="⛓️ Exile", value="Active" if has_exile else "Clear", inline=True)
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
                value=f"**Case #{latest['case_id']}** · By {mod_display}\n*{latest['reason']}*",
                inline=False,
            )
        embed.set_footer(text=f"{config.SERVER_NAME} · Audit Registry")
        await ctx.send(embed=embed)

    # ─── ANNOUNCE ────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="announce", description="Send an authority announcement.")
    @app_commands.describe(message="The authority message to publish.")
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def announce(self, ctx: commands.Context, *, message: str) -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return
        if not has_any_authority_role(ctx.author, config.ANNOUNCE_ALLOWED_ROLES):
            embed = discord.Embed(title="🚫 Access Denied", description="Official decrees are reserved for senior authority members.", color=discord.Color.red())
            embed.add_field(name="👑 Required Rank", value="\n".join(f"• {r}" for r in config.ANNOUNCE_ALLOWED_ROLES), inline=False)
            await ctx.send(embed=embed)
            return

        announcements_channel = get_text_channel_by_name(ctx.guild, config.ANNOUNCEMENTS_CHANNEL)
        if announcements_channel is None:
            await ctx.send(f'Authority channel not found. Create or rename to `{config.ANNOUNCEMENTS_CHANNEL}`.')
            return

        embed = discord.Embed(title="📣 Official Decree", description=message, color=config.ANNOUNCE_EMBED_COLOR)
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.add_field(name="🛡️ Issued By", value=ctx.author.mention, inline=True)
        embed.set_footer(text=f"{config.SERVER_NAME} · L'Mkhzen Authority System")

        try:
            await announcements_channel.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("Discord denied access to the announcements channel.")
            return

        await ctx.send(embed=discord.Embed(
            title="✅ Decree Delivered",
            description=f"Your announcement was posted to {announcements_channel.mention}.",
            color=discord.Color.dark_green(),
        ))

    # ─── PROMOTE ─────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="promote", description="Promote a member one tier up the authority hierarchy.")
    @app_commands.describe(member="The member to promote.", reason="Reason for the promotion.")
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def promote(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Merit recognized.") -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return
        if not has_any_authority_role(ctx.author, config.ANNOUNCE_ALLOWED_ROLES):
            await ctx.send("Only senior authority members may promote members.")
            return

        hierarchy = config.AUTHORITY_HIERARCHY
        current_rank = resolve_rank(member)

        try:
            current_index = hierarchy.index(current_rank)
        except ValueError:
            current_index = len(hierarchy)

        if current_index == 0:
            await ctx.send(embed=discord.Embed(
                title="👑 Already at the Top",
                description=f"{member.mention} already holds the highest rank.",
                color=discord.Color.orange(),
            ))
            return

        target_rank = hierarchy[current_index - 1]
        prestige_data = get_member_prestige(ctx.guild.id, member.id)
        prestige_score = prestige_data.get("prestige", 0)
        min_required = config.PRESTIGE_PROMOTION_MINIMUMS.get(target_rank, 0)

        prestige_warning = ""
        if prestige_score < min_required:
            if config.PRESTIGE_ENFORCE_MINIMUM:
                await ctx.send(embed=discord.Embed(
                    title="⭐ Insufficient Prestige",
                    description=f"{member.mention} needs **{min_required:,}** Prestige to be promoted to {target_rank}. Current: **{prestige_score:,}**.",
                    color=discord.Color.orange(),
                ))
                return
            prestige_warning = f"\n⚠️ *Below recommended Prestige ({prestige_score:,} / {min_required:,})*"

        old_role = get_role_by_name(ctx.guild, current_rank)
        new_role = get_role_by_name(ctx.guild, target_rank)

        if new_role is None:
            await ctx.send(f'Role `{target_rank}` not found in server. Create it first.')
            return

        logger.info("AUTHORITY | guild=%s | mod=%s | cmd=promote | target=%s | %s→%s", ctx.guild.id, ctx.author.id, member.id, current_rank, target_rank)

        try:
            if old_role and old_role in member.roles:
                await member.remove_roles(old_role, reason=f"Promoted by {ctx.author}")
            await member.add_roles(new_role, reason=f"Promoted by {ctx.author} | {reason}")
        except discord.Forbidden:
            await ctx.send("Discord denied the role change. Check that L'Mkhzen's role is above the target roles.")
            return

        try:
            tier_index = hierarchy.index(target_rank)
            badge = _TIER_BADGES[tier_index] if tier_index < len(_TIER_BADGES) else "🏅"
        except ValueError:
            badge = "🏅"

        embed = discord.Embed(
            title=f"{badge} Promotion Granted",
            description=f"{member.mention} has been elevated within the Medina.{prestige_warning}",
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="📍 From", value=current_rank if current_rank != "Unranked" else "*Unranked*", inline=True)
        embed.add_field(name="🏅 To", value=target_rank, inline=True)
        embed.add_field(name="🛡️ Promoted By", value=ctx.author.mention, inline=False)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text=f"{config.SERVER_NAME} · Promotion Registry")
        await ctx.send(embed=embed)

        log_channel = get_text_channel_by_name(ctx.guild, config.SERVER_LOGS_CHANNEL)
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass

    # ─── DEMOTE ──────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="demote", description="Demote a member one tier down the authority hierarchy.")
    @app_commands.describe(member="The member to demote.", reason="Reason for the demotion.")
    @commands.has_permissions(manage_roles=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def demote(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Authority decision.") -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return
        if not has_any_authority_role(ctx.author, config.ANNOUNCE_ALLOWED_ROLES):
            await ctx.send("Only senior authority members may demote members.")
            return

        hierarchy = config.AUTHORITY_HIERARCHY
        current_rank = resolve_rank(member)

        try:
            current_index = hierarchy.index(current_rank)
        except ValueError:
            await ctx.send(embed=discord.Embed(
                title="❔ No Rank to Demote From",
                description=f"{member.mention} does not hold a recognized authority rank.",
                color=discord.Color.greyple(),
            ))
            return

        if current_index >= len(hierarchy) - 1:
            await ctx.send(embed=discord.Embed(
                title="⛺ Already at the Bottom",
                description=f"{member.mention} already holds the lowest rank.",
                color=discord.Color.orange(),
            ))
            return

        target_rank = hierarchy[current_index + 1]
        old_role = get_role_by_name(ctx.guild, current_rank)
        new_role = get_role_by_name(ctx.guild, target_rank)

        if new_role is None:
            await ctx.send(f'Role `{target_rank}` not found in server. Create it first.')
            return

        logger.info("AUTHORITY | guild=%s | mod=%s | cmd=demote | target=%s | %s→%s", ctx.guild.id, ctx.author.id, member.id, current_rank, target_rank)

        try:
            if old_role and old_role in member.roles:
                await member.remove_roles(old_role, reason=f"Demoted by {ctx.author}")
            await member.add_roles(new_role, reason=f"Demoted by {ctx.author} | {reason}")
        except discord.Forbidden:
            await ctx.send("Discord denied the role change. Check that L'Mkhzen's role is above the target roles.")
            return

        new_prestige = reset_prestige_partial(ctx.guild.id, member.id, fraction=0.5)

        embed = discord.Embed(
            title="📉 Demotion Issued",
            description=f"{member.mention} has been reduced in the Medina's order.",
            color=discord.Color.dark_red(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="📍 From", value=current_rank, inline=True)
        embed.add_field(name="⬇️ To", value=target_rank, inline=True)
        embed.add_field(name="⭐ Prestige After", value=f"{new_prestige:,} *(−50% penalty)*", inline=True)
        embed.add_field(name="🛡️ Demoted By", value=ctx.author.mention, inline=False)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text=f"{config.SERVER_NAME} · Demotion Registry")
        await ctx.send(embed=embed)

        log_channel = get_text_channel_by_name(ctx.guild, config.SERVER_LOGS_CHANNEL)
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                pass

    # ─── STATS ───────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="stats", description="Show server statistics.")
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def stats(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return

        guild = ctx.guild
        total = guild.member_count or 0
        bots = sum(1 for m in guild.members if m.bot)
        humans = total - bots

        online = sum(
            1 for m in guild.members
            if not m.bot and m.status != discord.Status.offline
        )

        from utils.storage import get_active_exiles, load_warnings
        active_exiles = sum(len(v) for v in get_active_exiles().values())
        warnings_data = load_warnings()
        total_warnings = sum(
            len(cases)
            for guild_data in warnings_data.values()
            for cases in guild_data.values()
        )

        role_breakdown: list[str] = []
        for role_name in config.AUTHORITY_HIERARCHY[:6]:
            role = get_role_by_name(guild, role_name)
            if role:
                count = len([m for m in role.members if not m.bot])
                if count:
                    role_breakdown.append(f"{role_name}: **{count}**")

        embed = discord.Embed(
            title="📊 Medina Statistics",
            description=f"Current state of **{guild.name}**",
            color=discord.Color.dark_teal(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="👥 Total Members", value=str(total), inline=True)
        embed.add_field(name="🧑 Human Members", value=str(humans), inline=True)
        embed.add_field(name="🟢 Online", value=str(online), inline=True)
        embed.add_field(name="⛓️ Active Exiles", value=str(active_exiles), inline=True)
        embed.add_field(name="⚠️ Total Warnings on File", value=str(total_warnings), inline=True)
        if role_breakdown:
            embed.add_field(name="👑 Authority Breakdown", value="\n".join(role_breakdown), inline=False)
        embed.set_footer(text=f"{config.SERVER_NAME} · Live Statistics")
        await ctx.send(embed=embed)

    # ─── ERROR HANDLER ───────────────────────────────────────────────────────

    @rank.error
    @hierarchy.error
    @audit.error
    @announce.error
    @promote.error
    @demote.error
    @stats.error
    async def authority_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(embed=discord.Embed(
                title="⏱️ Slow Down",
                description=f"Try again in **{error.retry_after:.1f}s**.",
                color=discord.Color.orange(),
            ))
            return
        if isinstance(error, commands.MemberNotFound):
            await ctx.send("I could not find that member in this server.")
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: `{error.param.name}`.")
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not meet the Discord permission requirement.")
            return
        original_error = getattr(error, "original", error)
        if isinstance(original_error, discord.Forbidden):
            await ctx.send("Discord denied access to perform this action.")
            return
        raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Authority(bot))
