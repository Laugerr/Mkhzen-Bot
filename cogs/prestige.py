import logging
import time
import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils import config
from utils.authority import has_any_authority_role, resolve_rank
from utils.prestige import (
    add_message_xp,
    add_honour,
    apply_decay,
    get_member_prestige,
    get_guild_leaderboard,
)

logger = logging.getLogger(__name__)

_PRESTIGE_COLOR = config.PRESTIGE_EMBED_COLOR
_TIER_BADGES = ["👑", "🥇", "🥈", "🥉", "🏅", "🎖️", "⚜️", "📜", "🌿", "⛺"]


def _prestige_tier(score: int) -> tuple[str, str]:
    """Return (tier_label, badge) based on prestige score."""
    thresholds = [
        (5000, "⭐ Legendary", "🌟"),
        (2000, "💎 Diamond",   "💎"),
        (1000, "🏆 Platinum",  "🏆"),
        (500,  "🥇 Gold",      "🥇"),
        (200,  "🥈 Silver",    "🥈"),
        (50,   "🥉 Bronze",    "🥉"),
        (0,    "🔘 Newcomer",  "🔘"),
    ]
    for threshold, label, badge in thresholds:
        if score >= threshold:
            return label, badge
    return "🔘 Newcomer", "🔘"


class Prestige(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._xp_cooldown: dict[tuple[int, int], float] = {}
        self.decay_task.start()

    def cog_unload(self) -> None:
        self.decay_task.cancel()

    # ─── DECAY BACKGROUND TASK ───────────────────────────────────────────────

    @tasks.loop(hours=24)
    async def decay_task(self) -> None:
        for guild in self.bot.guilds:
            decayed = apply_decay(
                guild.id,
                config.PRESTIGE_DECAY_INACTIVE_DAYS,
                config.PRESTIGE_DECAY_AMOUNT,
            )
            if decayed:
                logger.info("Prestige decay applied to %s members in guild %s.", decayed, guild.id)

    @decay_task.before_loop
    async def before_decay(self) -> None:
        await self.bot.wait_until_ready()

    # ─── ON MESSAGE → AWARD XP ───────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        if not isinstance(message.author, discord.Member):
            return

        key = (message.guild.id, message.author.id)
        now = time.monotonic()
        if now - self._xp_cooldown.get(key, 0) < config.PRESTIGE_XP_COOLDOWN:
            return

        self._xp_cooldown[key] = now
        add_message_xp(
            guild_id=message.guild.id,
            member_id=message.author.id,
            amount=config.PRESTIGE_XP_PER_MESSAGE,
            daily_cap=config.PRESTIGE_DAILY_CAP,
        )

    # ─── /prestige ───────────────────────────────────────────────────────────

    @commands.hybrid_command(name="prestige", description="Check a member's Prestige score.")
    @app_commands.describe(member="The member to inspect. Leave empty for yourself.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def prestige(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return

        target = member or ctx.author
        if not isinstance(target, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return

        data = get_member_prestige(ctx.guild.id, target.id)
        score = data.get("prestige", 0)
        daily_xp = data.get("daily_xp", 0)
        honour_total = data.get("honour_total", 0)
        rank = resolve_rank(target)
        tier_label, tier_badge = _prestige_tier(score)

        # Progress bar toward next tier
        next_thresholds = [50, 200, 500, 1000, 2000, 5000]
        next_goal = next((t for t in next_thresholds if t > score), None)
        if next_goal:
            progress = min(score / next_goal, 1.0)
            filled = int(progress * 10)
            bar = "█" * filled + "░" * (10 - filled)
            progress_str = f"`{bar}` {score}/{next_goal}"
        else:
            progress_str = "🏆 *Maximum tier reached*"

        embed = discord.Embed(
            title=f"{tier_badge} Prestige Standing",
            description=f"Honour record for {target.mention}",
            color=_PRESTIGE_COLOR,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="⭐ Prestige", value=f"**{score:,}**", inline=True)
        embed.add_field(name="🏅 Tier", value=tier_label, inline=True)
        embed.add_field(name="👑 Authority Rank", value=rank, inline=True)
        embed.add_field(name="📈 Progress", value=progress_str, inline=False)
        embed.add_field(name="📅 Today's XP", value=f"{daily_xp} / {config.PRESTIGE_DAILY_CAP}", inline=True)
        embed.add_field(name="🎖️ Honour Granted", value=str(honour_total), inline=True)
        embed.set_footer(text=f"{config.SERVER_NAME} · Prestige Registry")
        await ctx.send(embed=embed)

    # ─── /leaderboard ────────────────────────────────────────────────────────

    @commands.hybrid_command(name="leaderboard", description="Show the top members by Prestige.")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def leaderboard(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return

        top = get_guild_leaderboard(ctx.guild.id, limit=10)
        if not top:
            await ctx.send(embed=discord.Embed(
                title="🏆 Prestige Leaderboard",
                description="No prestige data yet — start chatting to earn XP!",
                color=discord.Color.greyple(),
            ))
            return

        embed = discord.Embed(
            title="🏆 Prestige Leaderboard",
            description=f"Top members of **{config.SERVER_NAME}** by accumulated Prestige",
            color=_PRESTIGE_COLOR,
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        medals = ["🥇", "🥈", "🥉"]
        lines: list[str] = []
        for position, (member_id, data) in enumerate(top, start=1):
            score = data.get("prestige", 0)
            tier_label, _ = _prestige_tier(score)
            medal = medals[position - 1] if position <= 3 else f"**{position}.**"
            member = ctx.guild.get_member(member_id)
            name = member.mention if member else f"<@{member_id}>"
            lines.append(f"{medal} {name} — **{score:,}** ✨  *{tier_label}*")

        embed.add_field(name="📊 Rankings", value="\n".join(lines), inline=False)
        embed.set_footer(text=f"{config.SERVER_NAME} · Updated in real-time")
        await ctx.send(embed=embed)

    # ─── /honour ─────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="honour", description="Grant or deduct Prestige from a member. Staff only.")
    @app_commands.describe(
        member="The member to grant or deduct honour from.",
        amount="Positive to grant, negative to deduct (e.g. 50 or -20).",
        reason="Optional reason for the honour change.",
    )
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def honour(self, ctx: commands.Context, member: discord.Member, amount: int, *, reason: str = "Staff judgement.") -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return
        if not has_any_authority_role(ctx.author, config.ANNOUNCE_ALLOWED_ROLES):
            await ctx.send("Only senior authority members may grant or deduct honour.")
            return
        if amount == 0:
            await ctx.send("Amount must be non-zero.")
            return

        entry = add_honour(ctx.guild.id, member.id, amount)
        score = entry.get("prestige", 0)
        tier_label, tier_badge = _prestige_tier(score)

        action = "granted" if amount > 0 else "deducted"
        action_icon = "✨" if amount > 0 else "💔"

        embed = discord.Embed(
            title=f"{action_icon} Honour {action.capitalize()}",
            description=f"{member.mention}'s honour has been {action}.",
            color=discord.Color.dark_green() if amount > 0 else discord.Color.dark_red(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name=f"{action_icon} Change", value=f"**{'+' if amount > 0 else ''}{amount:,}** ✨", inline=True)
        embed.add_field(name="⭐ New Prestige", value=f"**{score:,}**", inline=True)
        embed.add_field(name="🏅 New Tier", value=f"{tier_badge} {tier_label}", inline=True)
        embed.add_field(name="🛡️ Issued By", value=ctx.author.mention, inline=True)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_footer(text=f"{config.SERVER_NAME} · Honour Registry")
        await ctx.send(embed=embed)

        logger.info(
            "PRESTIGE | guild=%s | mod=%s | cmd=honour | target=%s | amount=%s",
            ctx.guild.id, ctx.author.id, member.id, amount,
        )

    # ─── ERROR HANDLER ───────────────────────────────────────────────────────

    @prestige.error
    @leaderboard.error
    @honour.error
    async def prestige_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(embed=discord.Embed(
                title="⏱️ Slow Down",
                description=f"Try again in **{error.retry_after:.1f}s**.",
                color=discord.Color.orange(),
            ))
            return
        if isinstance(error, commands.MemberNotFound):
            await ctx.send("I could not find that member.")
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command.")
            return
        raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Prestige(bot))
