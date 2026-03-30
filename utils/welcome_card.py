from io import BytesIO
from pathlib import Path

import discord
from PIL import Image, ImageDraw, ImageOps

from utils import config


async def build_welcome_card(member: discord.Member) -> BytesIO | None:
    banner_path = Path(config.WELCOME_BANNER_PATH)
    if not banner_path.exists():
        return None

    avatar_asset = member.display_avatar.replace(size=256)
    avatar_bytes = await avatar_asset.read()

    with Image.open(banner_path).convert("RGBA") as banner:
        with Image.open(BytesIO(avatar_bytes)).convert("RGBA") as avatar:
            avatar_size = config.WELCOME_AVATAR_SIZE
            avatar = ImageOps.fit(avatar, (avatar_size, avatar_size), method=Image.Resampling.LANCZOS)

            mask = Image.new("L", (avatar_size, avatar_size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, avatar_size - 1, avatar_size - 1), fill=255)

            avatar.putalpha(mask)

            left = config.WELCOME_AVATAR_CENTER_X - (avatar_size // 2)
            top = config.WELCOME_AVATAR_CENTER_Y - (avatar_size // 2)
            banner.alpha_composite(avatar, (left, top))

        output = BytesIO()
        banner.save(output, format="PNG")
        output.seek(0)
        return output
