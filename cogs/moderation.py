import discord
from discord.ext import commands

from utils import config


def get_role_by_name(guild: discord.Guild, role_name: str) -> discord.Role | None:
    return discord.utils.get(guild.roles, name=role_name)


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided.") -> None:
        embed = discord.Embed(
            title="Formal Warning",
            color=config.MODERATION_EMBED_COLOR,
        )
        embed.add_field(name="Member", value=member.mention, inline=False)
        embed.add_field(name="Issued By", value=ctx.author.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="exile")
    @commands.has_permissions(manage_roles=True)
    async def exile(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Pending review.") -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
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

        await member.add_roles(quarantine_role, reason=f"Exiled by {ctx.author} | {reason}")

        embed = discord.Embed(
            title="Exile Enforced",
            description=f"{member.mention} has been moved under quarantine.",
            color=config.MODERATION_EMBED_COLOR,
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="pardon")
    @commands.has_permissions(manage_roles=True)
    async def pardon(self, ctx: commands.Context, member: discord.Member) -> None:
        if not ctx.guild:
            await ctx.send("This command can only be used inside a server.")
            return

        quarantine_role = get_role_by_name(ctx.guild, config.QUARANTINE_ROLE)
        if quarantine_role is None:
            await ctx.send(f'The role "{config.QUARANTINE_ROLE}" does not exist yet.')
            return

        if quarantine_role not in member.roles:
            await ctx.send(f"{member.mention} is not currently under quarantine.")
            return

        await member.remove_roles(quarantine_role, reason=f"Pardoned by {ctx.author}")

        embed = discord.Embed(
            title="Pardon Granted",
            description=f"{member.mention} has been released from quarantine.",
            color=discord.Color.dark_green(),
        )
        await ctx.send(embed=embed)

    @warn.error
    @exile.error
    @pardon.error
    async def moderation_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You must mention a member to use this command.")
            return

        if isinstance(error, commands.MemberNotFound):
            await ctx.send("I could not find that member in this server.")
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command.")
            return

        if isinstance(error, discord.Forbidden):
            await ctx.send("I do not have enough Discord permissions to manage that member or role.")
            return

        raise error


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
