import discord


def get_text_channel_by_name(guild: discord.Guild, channel_name: str) -> discord.TextChannel | None:
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    return channel if isinstance(channel, discord.TextChannel) else None
