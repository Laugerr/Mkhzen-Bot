import discord
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await ctx.send(f"Pong. Latency: `{latency_ms}ms`")

    @commands.command(name="about")
    async def about(self, ctx: commands.Context) -> None:
        description = (
            "Mkhzen is the authority system of Medina Hub: a structured Discord bot "
            "built around order, hierarchy, and server governance."
        )
        embed = discord.Embed(
            title="About Mkhzen",
            description=description,
            color=discord.Color.dark_gold(),
        )
        embed.set_footer(text="Medina Hub Authority System")
        await ctx.send(embed=embed)

    @commands.command(name="status")
    async def status(self, ctx: commands.Context) -> None:
        if not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return

        visible_roles = [role.mention for role in reversed(ctx.author.roles) if role.name != "@everyone"]
        role_display = ", ".join(visible_roles) if visible_roles else "No rank assigned."

        embed = discord.Embed(
            title="Authority Status",
            color=discord.Color.dark_teal(),
        )
        embed.add_field(name="Member", value=ctx.author.mention, inline=False)
        embed.add_field(name="Current Rank", value=role_display, inline=False)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
