import discord

from utils import config


def resolve_rank(member: discord.Member) -> str:
    member_role_names = {role.name for role in member.roles}
    for role_name in config.AUTHORITY_HIERARCHY:
        if role_name in member_role_names:
            return role_name
    return "Unranked"


def has_any_authority_role(member: discord.Member, allowed_roles: list[str]) -> bool:
    member_role_names = {role.name for role in member.roles}
    return any(role_name in member_role_names for role_name in allowed_roles)
