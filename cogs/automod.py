import logging
import time
from collections import defaultdict, deque

import discord
from discord.ext import commands

from utils import config
from utils.channels import get_text_channel_by_name
from utils.roles import get_role_by_name
from utils.storage import add_exile, add_warning, get_member_warnings
from utils.time_utils import format_duration, parse_duration

logger = logging.getLogger(__name__)


class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # {(guild_id, member_id): deque of monotonic timestamps}
        self._spam_tracker: dict[tuple[int, int], deque[float]] = defaultdict(deque)

    def _is_exempt(self, member: discord.Member, channel: discord.TextChannel) -> bool:
        """Return True if the member or channel should be ignored by auto-mod."""
        if not config.AUTOMOD_ENABLED:
            return True
        if channel.name in config.AUTOMOD_IGNORED_CHANNELS:
            return True
        member_role_names = {r.name for r in member.roles}
        return any(role in member_role_names for role in config.AUTOMOD_IGNORED_ROLES)

    async def _send_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        channel = get_text_channel_by_name(guild, config.SERVER_LOGS_CHANNEL)
        if channel is None:
            return
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    async def _issue_auto_warning(
        self,
        guild: discord.Guild,
        member: discord.Member,
        reason: str,
    ) -> None:
        """Record an automatic warning and trigger auto-exile if the threshold is reached."""
        bot_id = self.bot.user.id if self.bot.user else 0
        entry = add_warning(
            guild_id=guild.id,
            member_id=member.id,
            moderator_id=bot_id,
            reason=reason,
        )
        total = len(get_member_warnings(guild.id, member.id))

        # ── DM the member ────────────────────────────────────────────────────
        try:
            dm = discord.Embed(
                title="⚠️ Automatic Warning Issued",
                description=f"You have received an automatic warning in **{guild.name}**.",
                color=discord.Color(config.MODERATION_EMBED_COLOR),
            )
            dm.add_field(name="📝 Reason", value=reason, inline=False)
            dm.add_field(
                name="📊 Warning Count",
                value=f"**{total}** / {config.WARNING_EXILE_THRESHOLD} before auto-exile",
                inline=True,
            )
            dm.set_footer(text=f"{config.SERVER_NAME} · Auto-Moderation")
            await member.send(embed=dm)
        except discord.Forbidden:
            pass

        # ── Log to server-logs ───────────────────────────────────────────────
        log_embed = discord.Embed(
            title="⚠️ Auto-Mod Warning",
            description=f"{member.mention} received an automatic warning.",
            color=discord.Color(config.MODERATION_EMBED_COLOR),
        )
        log_embed.set_thumbnail(url=member.display_avatar.url)
        log_embed.add_field(name="🆔 Case", value=f"**#{entry['case_id']}**", inline=True)
        log_embed.add_field(name="📊 Total", value=str(total), inline=True)
        log_embed.add_field(name="📝 Reason", value=reason, inline=False)
        log_embed.set_footer(text=f"{config.SERVER_NAME} · Auto-Moderation")
        await self._send_log(guild, log_embed)

        logger.info(
            "AUTOMOD | warn | guild=%s | member=%s | total=%s | reason=%s",
            guild.id, member.id, total, reason,
        )

        # ── Auto-exile if threshold reached ──────────────────────────────────
        if total < config.WARNING_EXILE_THRESHOLD:
            return

        quarantine_role = get_role_by_name(guild, config.QUARANTINE_ROLE)
        if quarantine_role is None or quarantine_role in member.roles:
            return

        try:
            duration_seconds = parse_duration(config.WARNING_EXILE_DURATION)
            await member.add_roles(quarantine_role, reason=f"Auto-exile: {config.WARNING_EXILE_THRESHOLD} warnings reached.")
            exile_entry = add_exile(
                guild_id=guild.id,
                member_id=member.id,
                moderator_id=bot_id,
                reason=f"Automatic exile — {config.WARNING_EXILE_THRESHOLD} warnings reached.",
                duration_seconds=duration_seconds,
            )
            expires_ts = int(exile_entry["expires_at"])

            try:
                dm_exile = discord.Embed(
                    title="⛓️ Automatically Exiled",
                    description=f"You have been automatically exiled from **{guild.name}** after reaching the warning threshold.",
                    color=discord.Color.dark_red(),
                )
                dm_exile.add_field(name="⏳ Duration", value=format_duration(duration_seconds), inline=True)
                dm_exile.add_field(name="🕐 Expires", value=f"<t:{expires_ts}:R>", inline=True)
                dm_exile.add_field(name="📨 Appeal", value="Use `/appeal` once your exile ends to dispute this decision.", inline=False)
                dm_exile.set_footer(text=f"{config.SERVER_NAME} · Auto-Exile Notice")
                await member.send(embed=dm_exile)
            except discord.Forbidden:
                pass

            exile_log = discord.Embed(
                title="⛓️ Auto-Exile Triggered",
                description=f"{member.mention} automatically exiled after reaching {config.WARNING_EXILE_THRESHOLD} warnings.",
                color=discord.Color.dark_red(),
            )
            exile_log.set_thumbnail(url=member.display_avatar.url)
            exile_log.add_field(name="⏳ Duration", value=format_duration(duration_seconds), inline=True)
            exile_log.add_field(name="🕐 Expires", value=f"<t:{expires_ts}:F>", inline=False)
            exile_log.set_footer(text=f"{config.SERVER_NAME} · Auto-Moderation")
            await self._send_log(guild, exile_log)

            logger.info(
                "AUTOMOD | auto-exile | guild=%s | member=%s | threshold=%s",
                guild.id, member.id, config.WARNING_EXILE_THRESHOLD,
            )
        except (ValueError, discord.Forbidden) as e:
            logger.warning("AUTOMOD | auto-exile failed for %s in guild %s: %s", member.id, guild.id, e)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        if not isinstance(message.author, discord.Member):
            return
        if not isinstance(message.channel, discord.TextChannel):
            return
        if not config.AUTOMOD_ENABLED:
            return
        if self._is_exempt(message.author, message.channel):
            return

        now = time.monotonic()
        key = (message.guild.id, message.author.id)

        # ── Spam detection ───────────────────────────────────────────────────
        if config.AUTOMOD_SPAM_THRESHOLD > 0:
            timestamps = self._spam_tracker[key]
            timestamps.append(now)
            # Drop entries outside the rolling window
            while timestamps and timestamps[0] < now - config.AUTOMOD_SPAM_WINDOW:
                timestamps.popleft()

            if len(timestamps) >= config.AUTOMOD_SPAM_THRESHOLD:
                timestamps.clear()
                await self._issue_auto_warning(
                    message.guild,
                    message.author,
                    f"Automated: spam detected ({config.AUTOMOD_SPAM_THRESHOLD} messages in {config.AUTOMOD_SPAM_WINDOW}s).",
                )
                return  # Skip word filter; one violation at a time

        # ── Word filter ──────────────────────────────────────────────────────
        if config.AUTOMOD_BANNED_WORDS:
            content_lower = message.content.lower()
            for word in config.AUTOMOD_BANNED_WORDS:
                if word.lower() in content_lower:
                    try:
                        await message.delete()
                    except (discord.Forbidden, discord.NotFound):
                        pass
                    await self._issue_auto_warning(
                        message.guild,
                        message.author,
                        "Automated: prohibited content detected.",
                    )
                    return


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoMod(bot))
