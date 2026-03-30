import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
VERIFICATION_FILE = DATA_DIR / "verification.json"


def ensure_verification_file() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not VERIFICATION_FILE.exists():
        VERIFICATION_FILE.write_text("{}", encoding="utf-8")


def load_verification_registry() -> dict[str, dict[str, Any]]:
    ensure_verification_file()
    with VERIFICATION_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else {}


def save_verification_registry(data: dict[str, dict[str, Any]]) -> None:
    ensure_verification_file()
    with VERIFICATION_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def set_verification_message(
    guild_id: int,
    channel_id: int,
    message_id: int,
    role_name: str,
    remove_role_name: str,
    emoji: str,
) -> None:
    data = load_verification_registry()
    data[str(guild_id)] = {
        "channel_id": channel_id,
        "message_id": message_id,
        "role_name": role_name,
        "remove_role_name": remove_role_name,
        "emoji": emoji,
    }
    save_verification_registry(data)


def get_verification_message(guild_id: int) -> dict[str, Any] | None:
    data = load_verification_registry()
    return data.get(str(guild_id))
