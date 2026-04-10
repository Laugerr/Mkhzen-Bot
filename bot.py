import asyncio
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.validation import validate_asset_paths, validate_guild


BASE_DIR = Path(__file__).resolve().parent
COGS_DIR = BASE_DIR / "cogs"
WATCHING_STATUS = "\U0001f441\ufe0f L'Mkhzen is watching"


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


async def start_healthcheck_server() -> asyncio.AbstractServer | None:
    port = os.getenv("PORT")
    if not port:
        return None

    async def handle_healthcheck(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            await reader.read(1024)
            body = b"ok"
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/plain; charset=utf-8\r\n"
                b"Content-Length: 2\r\n"
                b"Connection: close\r\n"
                b"\r\n"
                + body
            )
            writer.write(response)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle_healthcheck, host="0.0.0.0", port=int(port))
    logging.info("Health check server listening on port %s", port)
    return server


class LMkhzenBot(commands.Bot):
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

        for issue in validate_asset_paths():
            logging.warning("Startup validation: %s", issue)

        for guild in self.guilds:
            issues = validate_guild(guild)
            if not issues:
                logging.info("Startup validation passed for guild: %s", guild.name)
                continue

            for issue in issues:
                logging.warning("Startup validation [%s]: %s", guild.name, issue)


async def main() -> None:
    configure_logging()
    load_dotenv()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set. Add it to your .env file.")

    healthcheck_server = await start_healthcheck_server()
    bot = LMkhzenBot()
    async with bot:
        try:
            await bot.start(token)
        finally:
            if healthcheck_server is not None:
                healthcheck_server.close()
                await healthcheck_server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot shutdown requested by user.")
