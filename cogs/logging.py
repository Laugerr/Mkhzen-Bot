import logging
import discord
from discord.ext import commands
from datetime import datetime, timezone

from utils.channels import get_text_channel_by_name
from utils import config

logger = logging.getLogger(__name__)

_ACTIVITY_COLOR = 0x3498DB
_LEAVE_COLOR = 0x95A5A6
_BAN_COLOR = 0xC0392B
_EDIT_COLOR = 0xF39C12
_DELETE_COLOR = 0xE74C3C
_ROLE_COLOR = 0x9B59B6


class Logging(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _send_activity(self, guild: discord.Guild, embed: discord.Embed) -> None:
        channel = get_text_channel_by_name(guild, config.ACTIVITY_LOGS_CHANNEL)
        if channel is None:
            return
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning("Cannot post to activity-logs in guild %s.", guild.id)

    async def _send_server_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        channel = get_text_channel_by_name(guild, config.SERVER_LOGS_CHANNEL)
        if channel is None:
            return
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning("Cannot post to server-logs in guild %s.", guild.id)

    # ─── MEMBER JOIN ─────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        now = datetime.now(timezone.utc)
        account_age = now - member.created_at.replace(tzinfo=timezone.utc)
        age_days = account_age.days

        age_warning = ""
        if age_days < 7:
            age_warning = f"\n⚠️ **New account** — only {age_days} day(s) old"

        embed = discord.Embed(
            title="📥 Member Joined",
            description=f"{member.mention} has entered the Medina.{age_warning}",
            color=_ACTIVITY_COLOR,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Username", value=str(member), inline=True)
        embed.add_field(name="🆔 User ID", value=str(member.id), inline=True)
        embed.add_field(
            name="📅 Account Created",
            value=f"<t:{int(member.created_at.timestamp())}:R>",
            inline=False,
        )
        embed.add_field(
            name="👥 Member Count",
            value=str(member.guild.member_count),
            inline=True,
        )
        embed.set_footer(text=f"{config.SERVER_NAME} · Join Log  ·  {now.strftime('%Y-%m-%d %H:%M UTC')}")
        await self._send_activity(member.guild, embed)

    # ─── MEMBER LEAVE ─────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
        role_display = " · ".join(roles) if roles else "*None*"

        time_in_server = ""
        if member.joined_at:
            delta = datetime.now(timezone.utc) - member.joined_at.replace(tzinfo=timezone.utc)
            days = delta.days
            time_in_server = f"{days} day{'s' if days != 1 else ''}"

        embed = discord.Embed(
            title="📤 Member Left",
            description=f"**{member}** has left the Medina.",
            color=_LEAVE_COLOR,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🆔 User ID", value=str(member.id), inline=True)
        embed.add_field(name="⏳ Time in Server", value=time_in_server or "Unknown", inline=True)
        embed.add_field(name="🎖️ Roles Held", value=role_display, inline=False)
        embed.set_footer(text=f"{config.SERVER_NAME} · Leave Log")
        await self._send_activity(member.guild, embed)

    # ─── MEMBER BAN ──────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User) -> None:
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"**{user}** has been permanently expelled from the Medina.",
            color=_BAN_COLOR,
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="👤 Username", value=str(user), inline=True)
        embed.add_field(name="🆔 User ID", value=str(user.id), inline=True)
        embed.set_footer(text=f"{config.SERVER_NAME} · Ban Log")
        await self._send_server_log(guild, embed)

    # ─── MESSAGE DELETE ───────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return

        content = (message.content or "*No text content*")[:1000]
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            color=_DELETE_COLOR,
        )
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.add_field(name="👤 Author", value=message.author.mention, inline=True)
        embed.add_field(name="📍 Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="📝 Content", value=content, inline=False)
        embed.set_footer(text=f"{config.SERVER_NAME} · Delete Log")
        await self._send_activity(message.guild, embed)

    # ─── MESSAGE EDIT ─────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.guild is None or after.author.bot:
            return
        if before.content == after.content:
            return

        before_content = (before.content or "*empty*")[:500]
        after_content = (after.content or "*empty*")[:500]

        embed = discord.Embed(
            title="✏️ Message Edited",
            color=_EDIT_COLOR,
        )
        embed.set_thumbnail(url=after.author.display_avatar.url)
        embed.add_field(name="👤 Author", value=after.author.mention, inline=True)
        embed.add_field(name="📍 Channel", value=after.channel.mention, inline=True)
        embed.add_field(name="📄 Before", value=before_content, inline=False)
        embed.add_field(name="📝 After", value=after_content, inline=False)
        if after.jump_url:
            embed.add_field(name="🔗 Jump", value=f"[View Message]({after.jump_url})", inline=False)
        embed.set_footer(text=f"{config.SERVER_NAME} · Edit Log")
        await self._send_activity(after.guild, embed)

    # ─── ROLE CHANGES ─────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        added = after_roles - before_roles
        removed = before_roles - after_roles

        if not added and not removed:
            return

        embed = discord.Embed(
            title="🎭 Roles Updated",
            description=f"Role changes for {after.mention}",
            color=_ROLE_COLOR,
        )
        embed.set_thumbnail(url=after.display_avatar.url)
        if added:
            embed.add_field(
                name="✅ Added",
                value=" · ".join(r.mention for r in added),
                inline=False,
            )
        if removed:
            embed.add_field(
                name="❌ Removed",
                value=" · ".join(r.mention for r in removed),
                inline=False,
            )
        embed.set_footer(text=f"{config.SERVER_NAME} · Role Log")
        await self._send_server_log(after.guild, embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Logging(bot))
