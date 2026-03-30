import discord
from discord.ext import commands

from utils import config
from utils.authority import has_any_authority_role, resolve_rank
from utils.channels import get_text_channel_by_name
from utils.storage import get_member_exile, get_member_warnings


class Authority(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="rank")
    async def rank(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        target = member or ctx.author
        if not isinstance(target, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return

        current_rank = resolve_rank(target)
        embed = discord.Embed(
            title="Authority Rank",
            color=discord.Color.dark_gold(),
        )
        embed.add_field(name="Member", value=target.mention, inline=False)
        embed.add_field(name="Hierarchy", value=current_rank, inline=False)
        embed.set_footer(text=f"Authority order of {config.SERVER_NAME}")
        await ctx.send(embed=embed)

    @commands.command(name="hierarchy")
    async def hierarchy(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            title="Authority Hierarchy",
            description=f"Recognized order within {config.SERVER_NAME}",
            color=discord.Color.dark_gold(),
        )

        hierarchy_lines = [
            f"{index}. {role_name}"
            for index, role_name in enumerate(config.AUTHORITY_HIERARCHY, start=1)
        ]
        embed.add_field(name="Rank Ladder", value="\n".join(hierarchy_lines), inline=False)
        embed.set_footer(text="Highest authority appears first")
        await ctx.send(embed=embed)

    @commands.command(name="audit")
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
        role_display = ", ".join(visible_roles) if visible_roles else "No visible roles."

        embed = discord.Embed(
            title="Authority Audit",
            description=f"System profile for {target.mention}",
            color=discord.Color.dark_teal(),
        )
        embed.add_field(name="Hierarchy", value=current_rank, inline=False)
        embed.add_field(name="Warnings", value=str(len(warning_entries)), inline=True)
        embed.add_field(name="Exile Status", value="Active" if exile_entry else "Clear", inline=True)
        embed.add_field(name="Roles", value=role_display, inline=False)

        if exile_entry:
            expires_at = int(float(exile_entry["expires_at"]))
            embed.add_field(name="Exile Ends", value=f"<t:{expires_at}:R>", inline=False)
            embed.add_field(name="Exile Reason", value=str(exile_entry["reason"]), inline=False)

        if warning_entries:
            latest_warning = warning_entries[-1]
            moderator = ctx.guild.get_member(int(latest_warning["moderator_id"]))
            moderator_display = moderator.mention if moderator else f"<@{latest_warning['moderator_id']}>"
            embed.add_field(
                name="Latest Warning",
                value=(
                    f"Case #{latest_warning['case_id']}\n"
                    f"Moderator: {moderator_display}\n"
                    f"Reason: {latest_warning['reason']}"
                ),
                inline=False,
            )

        embed.set_footer(text=f"{config.SERVER_NAME} | Audit Registry")
        await ctx.send(embed=embed)

    @commands.command(name="announce")
    @commands.has_permissions(manage_guild=True)
    async def announce(self, ctx: commands.Context, *, message: str) -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return

        if not has_any_authority_role(ctx.author, config.ANNOUNCE_ALLOWED_ROLES):
            allowed_roles = ", ".join(config.ANNOUNCE_ALLOWED_ROLES)
            await ctx.send(f"Authority denied. This decree is reserved for: {allowed_roles}.")
            return

        announcements_channel = get_text_channel_by_name(ctx.guild, config.ANNOUNCEMENTS_CHANNEL)
        if announcements_channel is None:
            await ctx.send(
                f'Authority channel not found. Create or rename the channel to "{config.ANNOUNCEMENTS_CHANNEL}".'
            )
            return

        embed = discord.Embed(
            title="Authority Announcement",
            description=message,
            color=config.ANNOUNCE_EMBED_COLOR,
        )
        embed.add_field(name="Issued By", value=ctx.author.mention, inline=False)
        embed.set_footer(text=f"{config.SERVER_NAME} | Mkhzen Authority System")

        try:
            await announcements_channel.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(
                "Authority denied by Discord. Make sure Mkhzen can view and send messages in the announcements channel."
            )
            return

        await ctx.send(f"Authority announcement delivered to {announcements_channel.mention}.")

    @rank.error
    @hierarchy.error
    @audit.error
    @announce.error
    async def authority_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
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
