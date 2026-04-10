import discord
from discord import app_commands
from discord.ext import commands

from utils.authority import resolve_rank


_LATENCY_TIERS = [
    (80,  "🟢 Excellent", discord.Color.brand_green()),
    (200, "🟡 Good",      discord.Color.yellow()),
    (400, "🟠 Slow",      discord.Color.orange()),
]


def _latency_meta(ms: int) -> tuple[str, discord.Color]:
    for threshold, label, color in _LATENCY_TIERS:
        if ms <= threshold:
            return label, color
    return "🔴 Lagging", discord.Color.brand_red()


class General(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Show the bot latency.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ping(self, ctx: commands.Context) -> None:
        ms = round(self.bot.latency * 1000)
        label, color = _latency_meta(ms)

        embed = discord.Embed(title="🏓 Pong!", color=color)
        embed.add_field(name="📡 Latency", value=f"`{ms} ms`", inline=True)
        embed.add_field(name="📶 Signal", value=label, inline=True)
        embed.set_footer(text="L'Mkhzen · Connection Status")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="about", description="Describe the L'Mkhzen authority system.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def about(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            title="👁️ L'Mkhzen",
            description=(
                "The authority system of **Medina Hub** — built around order, hierarchy, and server governance.\n\n"
                "Moderation, rank tracking, exile enforcement, and onboarding flow, all under one disciplined system."
            ),
            color=discord.Color.dark_gold(),
        )
        if ctx.guild and ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.add_field(name="⚔️ Moderation", value="Warnings · Exile · Pardon", inline=True)
        embed.add_field(name="👑 Authority", value="Ranks · Audit · Decrees", inline=True)
        embed.add_field(name="🚪 Onboarding", value="Welcome · Verify · Rules", inline=True)
        embed.set_footer(text="Medina Hub Authority System")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="status", description="Show your current visible roles in the server.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def status(self, ctx: commands.Context) -> None:
        if not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return

        rank = resolve_rank(ctx.author)
        visible_roles = [role.mention for role in reversed(ctx.author.roles) if role.name != "@everyone"]
        role_display = " · ".join(visible_roles) if visible_roles else "*No rank assigned.*"

        embed = discord.Embed(title="🪪 Authority Status", color=discord.Color.dark_teal())
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="👤 Member", value=ctx.author.mention, inline=True)
        embed.add_field(name="🏅 Standing", value=rank, inline=True)
        embed.add_field(name="🎖️ Roles", value=role_display, inline=False)
        embed.set_footer(text="Medina Hub · Identity Registry")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
