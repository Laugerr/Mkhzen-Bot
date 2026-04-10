import logging
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone

from utils import config
from utils.authority import has_any_authority_role
from utils.channels import get_text_channel_by_name
from utils.decrees import (
    add_decree, get_decrees, repeal_decree,
    add_appeal, get_appeals, resolve_appeal,
    add_vote, get_vote, cast_vote, close_vote, get_all_active_votes,
)
from utils.paginator import EmbedPaginator
from utils.roles import get_role_by_name
from utils.time_utils import parse_duration, format_duration

logger = logging.getLogger(__name__)

_GOV = config.GOVERNANCE_EMBED_COLOR
_GOLD = discord.Color.gold()
_GREEN = discord.Color.dark_green()
_RED = discord.Color.red()


# ─── VOTE VIEW ───────────────────────────────────────────────────────────────

class VoteView(discord.ui.View):
    def __init__(self, guild_id: int, vote_id: int) -> None:
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.vote_id = vote_id

        yes_btn = discord.ui.Button(
            label="✅  Aye",
            style=discord.ButtonStyle.success,
            custom_id=f"vote_{guild_id}_{vote_id}_yes",
        )
        no_btn = discord.ui.Button(
            label="❌  Nay",
            style=discord.ButtonStyle.danger,
            custom_id=f"vote_{guild_id}_{vote_id}_no",
        )
        yes_btn.callback = lambda i: self._record(i, "yes")
        no_btn.callback = lambda i: self._record(i, "no")
        self.add_item(yes_btn)
        self.add_item(no_btn)

    async def _record(self, interaction: discord.Interaction, choice: str) -> None:
        vote = get_vote(self.guild_id, self.vote_id)
        if vote is None or vote["status"] != "active":
            await interaction.response.send_message("⏱️ This vote has already closed.", ephemeral=True)
            return
        success = cast_vote(self.guild_id, self.vote_id, interaction.user.id, choice)
        if not success:
            await interaction.response.send_message("You have already cast your vote.", ephemeral=True)
            return
        vote = get_vote(self.guild_id, self.vote_id)
        yes = len(vote["yes_votes"])
        no = len(vote["no_votes"])
        label = "✅ Aye" if choice == "yes" else "❌ Nay"
        await interaction.response.send_message(
            f"**{label}** recorded.  Current tally: **{yes}** Aye  ·  **{no}** Nay",
            ephemeral=True,
        )


# ─── INTEREST ROLE SELECT ─────────────────────────────────────────────────────

class RoleSelectView(discord.ui.View):
    def __init__(self, options: list[discord.SelectOption], guild: discord.Guild) -> None:
        super().__init__(timeout=120)
        self.guild = guild
        select = discord.ui.Select(
            placeholder="Choose your interests…",
            min_values=0,
            max_values=len(options),
            options=options,
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This can only be used inside a server.", ephemeral=True)
            return

        member = interaction.user
        selected_names = set(interaction.data.get("values", []))  # type: ignore[arg-type]

        added, already = [], []
        for role_name in config.INTEREST_ROLES:
            role = get_role_by_name(self.guild, role_name)
            if role is None:
                continue
            if role_name in selected_names:
                if role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Interest role self-selection.")
                        added.append(role.mention)
                    except discord.Forbidden:
                        pass
                else:
                    already.append(role.mention)

        parts = []
        if added:
            parts.append(f"✅ Added: {', '.join(added)}")
        if already:
            parts.append(f"ℹ️ Already held: {', '.join(already)}")
        if not parts:
            parts.append("No changes made.")

        await interaction.response.send_message("\n".join(parts), ephemeral=True)


class Governance(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.vote_close_task.start()

    def cog_unload(self) -> None:
        self.vote_close_task.cancel()

    # ─── VOTE CLOSE TASK ─────────────────────────────────────────────────────

    @tasks.loop(seconds=60)
    async def vote_close_task(self) -> None:
        now = datetime.now(timezone.utc).timestamp()
        for guild_id_str, votes in get_all_active_votes().items():
            guild = self.bot.get_guild(int(guild_id_str))
            if guild is None:
                continue
            for vote in votes:
                if float(vote["ends_at"]) > now:
                    continue
                closed = close_vote(int(guild_id_str), int(vote["vote_id"]))
                if closed is None:
                    continue
                await self._post_vote_results(guild, closed)

    @vote_close_task.before_loop
    async def before_vote_close(self) -> None:
        await self.bot.wait_until_ready()

    async def _post_vote_results(self, guild: discord.Guild, vote: dict) -> None:
        channel = guild.get_channel(int(vote["channel_id"]))
        if not isinstance(channel, discord.TextChannel):
            return
        yes = len(vote["yes_votes"])
        no = len(vote["no_votes"])
        total = yes + no
        winner = "✅ Aye" if yes > no else ("❌ Nay" if no > yes else "⚖️ Tied")

        embed = discord.Embed(
            title="📊 Vote Closed — Results",
            description=f"**{vote['question']}**",
            color=_GOLD,
        )
        embed.add_field(name="✅ Aye", value=str(yes), inline=True)
        embed.add_field(name="❌ Nay", value=str(no), inline=True)
        embed.add_field(name="🗳️ Total Votes", value=str(total), inline=True)
        embed.add_field(name="⚖️ Verdict", value=f"**{winner}**", inline=False)
        embed.set_footer(text=f"{config.SERVER_NAME} · Council Vote")
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning("Cannot post vote results in guild %s channel %s.", guild.id, channel.id)

    # ─── /decree ─────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="decree", description="Issue an official decree and archive it.")
    @app_commands.describe(title="Short title for the decree.", content="Full text of the decree.")
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def decree(self, ctx: commands.Context, title: str, *, content: str) -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return
        if not has_any_authority_role(ctx.author, config.ANNOUNCE_ALLOWED_ROLES):
            await ctx.send("Only senior authority members may issue decrees.")
            return

        entry = add_decree(ctx.guild.id, ctx.author.id, title, content)

        embed = discord.Embed(
            title=f"📜 Decree #{entry['decree_id']} — {entry['title']}",
            description=entry["content"],
            color=_GOV,
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.add_field(name="🛡️ Issued By", value=ctx.author.mention, inline=True)
        embed.add_field(name="🆔 Decree #", value=str(entry["decree_id"]), inline=True)
        embed.set_footer(text=f"{config.SERVER_NAME} · Official Decree Registry")

        ann_channel = get_text_channel_by_name(ctx.guild, config.ANNOUNCEMENTS_CHANNEL)
        if ann_channel:
            try:
                await ann_channel.send(embed=embed)
            except discord.Forbidden:
                pass

        confirm = discord.Embed(
            title="✅ Decree Issued",
            description=f"Decree **#{entry['decree_id']}** — *{entry['title']}* has been archived and posted.",
            color=_GREEN,
        )
        await ctx.send(embed=confirm)
        logger.info("GOVERNANCE | guild=%s | author=%s | cmd=decree | id=%s", ctx.guild.id, ctx.author.id, entry["decree_id"])

    # ─── /decrees ────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="decrees", description="Browse the official decree archive.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def decrees(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return

        all_decrees = [d for d in get_decrees(ctx.guild.id)]
        if not all_decrees:
            await ctx.send(embed=discord.Embed(
                title="📜 Decree Archive",
                description="No decrees have been issued yet.",
                color=discord.Color.greyple(),
            ))
            return

        pages: list[discord.Embed] = []
        chunks = [all_decrees[i:i + 3] for i in range(0, len(all_decrees), 3)]
        for page_num, chunk in enumerate(chunks, 1):
            embed = discord.Embed(
                title="📜 Decree Archive",
                description=f"Official decrees of **{config.SERVER_NAME}**",
                color=_GOV,
            )
            if ctx.guild.icon:
                embed.set_thumbnail(url=ctx.guild.icon.url)
            for d in chunk:
                status_icon = "✅" if d["status"] == "active" else "🚫"
                ts = datetime.fromisoformat(d["timestamp"])
                embed.add_field(
                    name=f"{status_icon} #{d['decree_id']} — {d['title']}",
                    value=f"{d['content'][:200]}{'…' if len(d['content']) > 200 else ''}\n*Issued <t:{int(ts.timestamp())}:R>*",
                    inline=False,
                )
            embed.set_footer(text=f"{config.SERVER_NAME} · Page {page_num} of {len(chunks)}")
            pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            await ctx.send(embed=pages[0], view=EmbedPaginator(pages))

    # ─── /repeal ─────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="repeal", description="Repeal an active decree by ID.")
    @app_commands.describe(decree_id="The decree number to repeal.")
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def repeal(self, ctx: commands.Context, decree_id: int) -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return
        if not has_any_authority_role(ctx.author, config.ANNOUNCE_ALLOWED_ROLES):
            await ctx.send("Only senior authority members may repeal decrees.")
            return

        entry = repeal_decree(ctx.guild.id, decree_id)
        if entry is None:
            await ctx.send(embed=discord.Embed(
                title="❌ Not Found",
                description=f"No active decree **#{decree_id}** exists.",
                color=_RED,
            ))
            return

        embed = discord.Embed(
            title="🚫 Decree Repealed",
            description=f"Decree **#{entry['decree_id']}** — *{entry['title']}* has been repealed.",
            color=_RED,
        )
        embed.add_field(name="🛡️ Repealed By", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed)

    # ─── /vote ───────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="vote", description="Open a council vote. Members vote Aye or Nay.")
    @app_commands.describe(
        question="The question put to the council.",
        duration="How long the vote stays open (e.g. 1h, 24h, 2d). Default: 24h.",
    )
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 60, commands.BucketType.guild)
    async def vote(self, ctx: commands.Context, question: str, duration: str = "24h") -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return
        if not has_any_authority_role(ctx.author, config.MODERATION_ALLOWED_ROLES):
            await ctx.send("Only authority members may open council votes.")
            return

        try:
            duration_seconds = parse_duration(duration)
        except ValueError as e:
            await ctx.send(embed=discord.Embed(title="❌ Invalid Duration", description=str(e), color=_RED))
            return

        ends_ts = int(datetime.now(timezone.utc).timestamp()) + duration_seconds

        embed = discord.Embed(
            title="🗳️ Council Vote",
            description=f"**{question}**",
            color=_GOV,
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.add_field(name="🛡️ Opened By", value=ctx.author.mention, inline=True)
        embed.add_field(name="⏳ Closes", value=f"<t:{ends_ts}:R>", inline=True)
        embed.add_field(name="✅ Aye", value="0", inline=True)
        embed.add_field(name="❌ Nay", value="0", inline=True)
        embed.set_footer(text=f"{config.SERVER_NAME} · Cast your vote below")

        message = await ctx.send(embed=embed)
        actual_message = await ctx.channel.fetch_message(message.id) if ctx.interaction else message

        vote_entry = add_vote(
            guild_id=ctx.guild.id,
            author_id=ctx.author.id,
            question=question,
            duration_seconds=duration_seconds,
            channel_id=ctx.channel.id,
            message_id=actual_message.id,
        )

        view = VoteView(ctx.guild.id, vote_entry["vote_id"])
        await actual_message.edit(embed=embed, view=view)
        logger.info("GOVERNANCE | guild=%s | author=%s | cmd=vote | id=%s", ctx.guild.id, ctx.author.id, vote_entry["vote_id"])

    # ─── /appeal ─────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="appeal", description="Submit an appeal to the server staff.")
    @app_commands.describe(reason="Describe what you are appealing and why.")
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def appeal(self, ctx: commands.Context, *, reason: str) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return

        entry = add_appeal(ctx.guild.id, ctx.author.id, reason)

        staff_channel = get_text_channel_by_name(ctx.guild, config.STAFF_CHAT_CHANNEL)
        if staff_channel:
            staff_embed = discord.Embed(
                title=f"📨 New Appeal — #{entry['appeal_id']}",
                description=entry["reason"],
                color=_GOLD,
            )
            staff_embed.set_thumbnail(url=ctx.author.display_avatar.url)
            staff_embed.add_field(name="👤 Member", value=ctx.author.mention, inline=True)
            staff_embed.add_field(name="🆔 Appeal #", value=str(entry["appeal_id"]), inline=True)
            staff_embed.set_footer(text=f"Use /resolve {entry['appeal_id']} <note> to close this appeal.")
            try:
                await staff_channel.send(embed=staff_embed)
            except discord.Forbidden:
                logger.warning("Cannot post appeal to staff-chat in guild %s.", ctx.guild.id)

        confirm = discord.Embed(
            title="📨 Appeal Submitted",
            description=f"Your appeal **#{entry['appeal_id']}** has been delivered to the staff.",
            color=_GREEN,
        )
        confirm.add_field(name="📝 Your Plea", value=entry["reason"][:300], inline=False)
        confirm.set_footer(text="Staff will review and respond. Please be patient.")
        await ctx.send(embed=confirm, ephemeral=True if ctx.interaction else False)

    # ─── /appeals ────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="appeals", description="List open member appeals. Staff only.")
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def appeals(self, ctx: commands.Context) -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return
        if not has_any_authority_role(ctx.author, config.MODERATION_ALLOWED_ROLES):
            await ctx.send("Only authority members may view the appeal docket.")
            return

        open_appeals = get_appeals(ctx.guild.id, status="open")
        if not open_appeals:
            await ctx.send(embed=discord.Embed(
                title="📋 Appeal Docket",
                description="No open appeals — the docket is clear.",
                color=_GREEN,
            ))
            return

        pages: list[discord.Embed] = []
        chunks = [open_appeals[i:i + 5] for i in range(0, len(open_appeals), 5)]
        for page_num, chunk in enumerate(chunks, 1):
            embed = discord.Embed(
                title="📋 Open Appeals",
                description=f"{len(open_appeals)} appeal(s) awaiting review",
                color=_GOLD,
            )
            for ap in chunk:
                ts = datetime.fromisoformat(ap["created_at"])
                embed.add_field(
                    name=f"📨 Appeal #{ap['appeal_id']} — <@{ap['member_id']}>",
                    value=f"{ap['reason'][:200]}\n*Submitted <t:{int(ts.timestamp())}:R>*",
                    inline=False,
                )
            embed.set_footer(text=f"{config.SERVER_NAME} · Page {page_num} of {len(chunks)}  ·  Use /resolve <id> <note> to close")
            pages.append(embed)

        if len(pages) == 1:
            await ctx.send(embed=pages[0])
        else:
            await ctx.send(embed=pages[0], view=EmbedPaginator(pages))

    # ─── /resolve ────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="resolve", description="Resolve an open member appeal.")
    @app_commands.describe(appeal_id="The appeal number to resolve.", note="Your resolution note to the member.")
    @commands.has_permissions(manage_messages=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def resolve(self, ctx: commands.Context, appeal_id: int, *, note: str = "Reviewed and closed.") -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return
        if not has_any_authority_role(ctx.author, config.MODERATION_ALLOWED_ROLES):
            await ctx.send("Only authority members may resolve appeals.")
            return

        entry = resolve_appeal(ctx.guild.id, appeal_id, ctx.author.id, note)
        if entry is None:
            await ctx.send(embed=discord.Embed(
                title="❌ Not Found",
                description=f"No open appeal **#{appeal_id}** found.",
                color=_RED,
            ))
            return

        embed = discord.Embed(
            title="✅ Appeal Resolved",
            description=f"Appeal **#{entry['appeal_id']}** has been closed.",
            color=_GREEN,
        )
        embed.add_field(name="👤 Member", value=f"<@{entry['member_id']}>", inline=True)
        embed.add_field(name="🛡️ Resolved By", value=ctx.author.mention, inline=True)
        embed.add_field(name="📝 Resolution Note", value=note, inline=False)
        await ctx.send(embed=embed)

        member = ctx.guild.get_member(int(entry["member_id"]))
        if member:
            try:
                dm_embed = discord.Embed(
                    title="📨 Your Appeal Has Been Reviewed",
                    description=f"Your appeal in **{ctx.guild.name}** has been resolved.",
                    color=_GREEN,
                )
                dm_embed.add_field(name="📝 Staff Note", value=note, inline=False)
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass

        logger.info("GOVERNANCE | guild=%s | mod=%s | cmd=resolve | appeal=%s", ctx.guild.id, ctx.author.id, appeal_id)

    # ─── /roles ──────────────────────────────────────────────────────────────

    @commands.hybrid_command(name="roles", description="Browse and select your interest roles.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def roles(self, ctx: commands.Context) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return

        if not config.INTEREST_ROLES:
            await ctx.send(embed=discord.Embed(
                title="🎭 Interest Roles",
                description="No interest roles have been configured for this server yet.",
                color=discord.Color.greyple(),
            ))
            return

        options: list[discord.SelectOption] = []
        for role_name in config.INTEREST_ROLES:
            role = get_role_by_name(ctx.guild, role_name)
            if role is not None:
                options.append(discord.SelectOption(label=role_name, value=role_name))

        if not options:
            await ctx.send("No interest roles were found in the server.")
            return

        embed = discord.Embed(
            title="🎭 Interest Roles",
            description="Select the roles that match your interests. You can pick as many as you like.",
            color=discord.Color.purple(),
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text="Your selection is applied immediately.")

        view = RoleSelectView(options, ctx.guild)
        await ctx.send(embed=embed, view=view)

    # ─── ERROR HANDLER ───────────────────────────────────────────────────────

    @decree.error
    @decrees.error
    @repeal.error
    @vote.error
    @appeal.error
    @appeals.error
    @resolve.error
    @roles.error
    async def governance_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(embed=discord.Embed(
                title="⏱️ Slow Down",
                description=f"Try again in **{error.retry_after:.1f}s**.",
                color=discord.Color.orange(),
            ), ephemeral=True if ctx.interaction else False)
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command.")
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: `{error.param.name}`.")
            return
        raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Governance(bot))
