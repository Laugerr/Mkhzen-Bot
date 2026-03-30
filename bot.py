import asyncio
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
COGS_DIR = BASE_DIR / "cogs"
WATCHING_STATUS = "\U0001f441\ufe0f Mkhzen is watching"


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def discover_extensions() -> list[str]:
    if not COGS_DIR.exists():
        return []

    return sorted(
        f"cogs.{path.stem}"
        for path in COGS_DIR.glob("*.py")
        if path.name != "__init__.py"
    )


class MkhzenBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        for extension in discover_extensions():
            try:
                await self.load_extension(extension)
                logging.info("Loaded extension: %s", extension)
            except Exception:
                logging.exception("Failed to load extension: %s", extension)

        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id and guild_id.isdigit():
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logging.info("Synced %s slash commands to guild %s", len(synced), guild_id)
            return

        synced = await self.tree.sync()
        logging.info("Synced %s global slash commands", len(synced))

    async def on_ready(self) -> None:
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=WATCHING_STATUS,
        )
        await self.change_presence(activity=activity)
        logging.info("Connected as %s (%s)", self.user, self.user.id if self.user else "unknown")


async def main() -> None:
    configure_logging()
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set. Add it to your .env file.")

    bot = MkhzenBot()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot shutdown requested by user.")
