from pathlib import Path

import discord

from utils import config
from utils.channels import get_text_channel_by_name


REQUIRED_ROLE_NAMES = [
    config.SULTAN_ROLE,
    config.WALI_ROLE,
    config.QAID_ROLE,
    config.SHEIKH_ROLE,
    config.MQADDEM_ROLE,
    config.FQIHS_ROLE,
    config.AHL_AL_MEDINA_ROLE,
    config.TALEBS_ROLE,
    config.NOMADS_ROLE,
    config.TRAVELER_ROLE,
    config.QUARANTINE_ROLE,
    config.VERIFIED_ROLE,
    config.UNVERIFIED_ROLE,
]

REQUIRED_CHANNEL_NAMES = [
    config.SERVER_LOGS_CHANNEL,
    config.ANNOUNCEMENTS_CHANNEL,
    config.WELCOME_CHANNEL,
    config.VERIFY_CHANNEL,
    config.RULES_CHANNEL,
]


def validate_asset_paths() -> list[str]:
    issues: list[str] = []
    banner_path = Path(config.WELCOME_BANNER_PATH)
    if not banner_path.exists():
        issues.append(f"Missing welcome banner asset: {banner_path}")
    return issues


def validate_guild(guild: discord.Guild) -> list[str]:
    issues: list[str] = []

    guild_role_names = {role.name for role in guild.roles}
    for role_name in REQUIRED_ROLE_NAMES:
        if role_name not in guild_role_names:
            issues.append(f"Missing role: {role_name}")

    for channel_name in REQUIRED_CHANNEL_NAMES:
        if get_text_channel_by_name(guild, channel_name) is None:
            issues.append(f"Missing channel: {channel_name}")

    return issues
