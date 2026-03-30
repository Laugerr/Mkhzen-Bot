import discord
from discord.ext import commands
from pathlib import Path

from utils import config
from utils.channels import get_text_channel_by_name
from utils.verification import get_verification_message, set_verification_message
from utils.welcome_card import build_welcome_card


class Onboarding(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def get_role_by_name(guild: discord.Guild, role_name: str) -> discord.Role | None:
        return discord.utils.get(guild.roles, name=role_name)

    async def send_welcome_message(self, member: discord.Member) -> bool:
        guild = member.guild
        welcome_channel = get_text_channel_by_name(guild, config.WELCOME_CHANNEL)
        if welcome_channel is None:
            return False

        welcome_file: discord.File | None = None
        welcome_card = await build_welcome_card(member)
        if welcome_card is not None:
            welcome_file = discord.File(welcome_card, filename="welcome-card.png")
        else:
            banner_path = Path(config.WELCOME_BANNER_PATH)
            if banner_path.exists():
                welcome_file = discord.File(banner_path, filename=banner_path.name)

        try:
            if welcome_file:
                await welcome_channel.send(file=welcome_file)
            else:
                verify_channel = get_text_channel_by_name(guild, config.VERIFY_CHANNEL)
                verify_reference = verify_channel.mention if verify_channel else "the verification channel"
                await welcome_channel.send(
                    f"Welcome to {config.SERVER_NAME}, {member.mention}. Present yourself in {verify_reference}."
                )
        except discord.Forbidden:
            return False

        return True

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        await self.send_welcome_message(member)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.guild_id is None:
            return

        if self.bot.user and payload.user_id == self.bot.user.id:
            return

        registry_entry = get_verification_message(payload.guild_id)
        if registry_entry is None:
            return

        if int(registry_entry["message_id"]) != payload.message_id:
            return

        if str(payload.emoji) != str(registry_entry["emoji"]):
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        member = payload.member or guild.get_member(payload.user_id)
        if member is None or member.bot:
            return

        verified_role = self.get_role_by_name(guild, str(registry_entry["role_name"]))
        unverified_role_name = str(registry_entry.get("remove_role_name", ""))
        unverified_role = self.get_role_by_name(guild, unverified_role_name) if unverified_role_name else None

        if verified_role is None or verified_role in member.roles:
            return

        try:
            await member.add_roles(verified_role, reason="Reaction verification completed.")
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role, reason="Reaction verification completed.")
        except discord.Forbidden:
            return

    @commands.hybrid_command(name="setupverify", description="Post the reaction verification message in the verify channel.")
    @commands.has_permissions(manage_guild=True)
    async def setupverify(self, ctx: commands.Context) -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return

        verify_channel = get_text_channel_by_name(ctx.guild, config.VERIFY_CHANNEL)
        if verify_channel is None:
            await ctx.send(
                f'Verification channel not found. Create or rename the channel to "{config.VERIFY_CHANNEL}".'
            )
            return

        verified_role = self.get_role_by_name(ctx.guild, config.VERIFIED_ROLE)
        if verified_role is None:
            await ctx.send(
                f'Verified role not found. Create or rename the role to "{config.VERIFIED_ROLE}" first.'
            )
            return

        unverified_role = self.get_role_by_name(ctx.guild, config.UNVERIFIED_ROLE)
        if unverified_role is None:
            await ctx.send(
                f'Unverified role not found. Create or rename the role to "{config.UNVERIFIED_ROLE}" first.'
            )
            return

        rules_channel = get_text_channel_by_name(ctx.guild, config.RULES_CHANNEL)
        rules_reference = rules_channel.mention if rules_channel else f"`{config.RULES_CHANNEL}`"

        embed = discord.Embed(
            title="Medina Verification Gate",
            description=(
                "Pass the gate to enter the Medina properly.\n"
                f"React with {config.VERIFY_REACTION_EMOJI} below to complete verification."
            ),
            color=discord.Color.dark_gold(),
        )
        embed.add_field(name="Rules", value=f"Read {rules_reference} before verifying.", inline=False)
        embed.add_field(
            name="Role Transition",
            value=f"You will receive {verified_role.mention} and leave {unverified_role.mention}.",
            inline=False,
        )
        embed.add_field(
            name="Instruction",
            value=f"React with {config.VERIFY_REACTION_EMOJI} on this message to confirm entry.",
            inline=False,
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text="L'Mkhzen | Medina Hub Verification Registry")

        try:
            message = await verify_channel.send(embed=embed)
            await message.add_reaction(config.VERIFY_REACTION_EMOJI)
        except discord.Forbidden:
            await ctx.send(
                "L'Mkhzen cannot send or react in the verification channel. Check channel permissions."
            )
            return

        set_verification_message(
            guild_id=ctx.guild.id,
            channel_id=verify_channel.id,
            message_id=message.id,
            role_name=verified_role.name,
            remove_role_name=unverified_role.name,
            emoji=config.VERIFY_REACTION_EMOJI,
        )
        await ctx.send(f"Verification panel created in {verify_channel.mention}.")

    @commands.hybrid_command(name="setuprules", description="Post a rules panel in the rules channel.")
    @commands.has_permissions(manage_guild=True)
    async def setuprules(self, ctx: commands.Context) -> None:
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return

        rules_channel = get_text_channel_by_name(ctx.guild, config.RULES_CHANNEL)
        if rules_channel is None:
            await ctx.send(
                f'Rules channel not found. Create or rename the channel to "{config.RULES_CHANNEL}".'
            )
            return

        verify_channel = get_text_channel_by_name(ctx.guild, config.VERIFY_CHANNEL)
        verify_reference = verify_channel.mention if verify_channel else f"`{config.VERIFY_CHANNEL}`"

        embed = discord.Embed(
            title="Medina Code",
            description="Read and respect the law of the Medina.",
            color=discord.Color.dark_gold(),
        )
        embed.add_field(
            name="1. Respect the Medina",
            value="Show respect to members, staff, and the structure of the server.",
            inline=False,
        )
        embed.add_field(
            name="2. No Disruption",
            value="Spam, harassment, hate, and repeated disturbance are not tolerated.",
            inline=False,
        )
        embed.add_field(
            name="3. Follow Authority Guidance",
            value="Honor moderation decisions and use the proper channels for appeals or questions.",
            inline=False,
        )
        embed.add_field(
            name="4. Verification Flow",
            value=f"If you are not yet admitted, return to {verify_reference} and complete verification.",
            inline=False,
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        embed.set_footer(text="L'Mkhzen | Medina Hub Rules Registry")

        try:
            await rules_channel.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("L'Mkhzen cannot send messages in the rules channel. Check channel permissions.")
            return

        await ctx.send(f"Rules panel created in {rules_channel.mention}.")

    @commands.hybrid_command(name="testwelcome", description="Send a test welcome message for yourself.")
    @commands.has_permissions(manage_guild=True)
    async def testwelcome(self, ctx: commands.Context) -> None:
        if not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used inside a server.")
            return

        sent = await self.send_welcome_message(ctx.author)
        if sent:
            await ctx.send("Test welcome message delivered.")
            return

        await ctx.send(
            "Welcome message could not be sent. Check the welcome channel name and L'Mkhzen's channel permissions."
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Onboarding(bot))
