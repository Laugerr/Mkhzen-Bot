import discord


def normalize_channel_name(channel_name: str) -> str:
    translation = str.maketrans({
        "┃": "|",
        "│": "|",
        "｜": "|",
        " ": "",
    })
    return channel_name.translate(translation).casefold()


def get_text_channel_by_name(guild: discord.Guild, channel_name: str) -> discord.TextChannel | None:
    exact_match = discord.utils.get(guild.text_channels, name=channel_name)
    if isinstance(exact_match, discord.TextChannel):
        return exact_match

    normalized_target = normalize_channel_name(channel_name)
    for channel in guild.text_channels:
        if normalize_channel_name(channel.name) == normalized_target:
            return channel

    return None
