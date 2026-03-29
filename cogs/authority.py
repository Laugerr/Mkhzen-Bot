import discord
from discord.ext import commands

from utils import config


def resolve_rank(member: discord.Member) -> str:
    member_role_names = {role.name for role in member.roles}
    for role_name in config.AUTHORITY_HIERARCHY:
        if role_name in member_role_names:
            return role_name
    return "Unranked"


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

    @commands.command(name="announce")
    @commands.has_permissions(manage_guild=True)
    async def announce(self, ctx: commands.Context, *, message: str) -> None:
        embed = discord.Embed(
            title="Authority Announcement",
            description=message,
            color=config.ANNOUNCE_EMBED_COLOR,
        )
        embed.add_field(name="Issued By", value=ctx.author.mention, inline=False)
        embed.set_footer(text=f"{config.SERVER_NAME} | Mkhzen Authority System")
        await ctx.send(embed=embed)

    @rank.error
    @announce.error
    async def authority_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MemberNotFound):
            await ctx.send("I could not find that member in this server.")
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You must provide a message for the announcement.")
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to issue authority announcements.")
            return

        raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Authority(bot))
