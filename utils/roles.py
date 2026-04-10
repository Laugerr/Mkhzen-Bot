import discord


def get_role_by_name(guild: discord.Guild, role_name: str) -> discord.Role | None:
    return discord.utils.get(guild.roles, name=role_name)
