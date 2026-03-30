import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
WARNINGS_FILE = DATA_DIR / "warnings.json"
EXILES_FILE = DATA_DIR / "exiles.json"


def ensure_data_files() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not WARNINGS_FILE.exists():
        WARNINGS_FILE.write_text("{}", encoding="utf-8")
    if not EXILES_FILE.exists():
        EXILES_FILE.write_text("{}", encoding="utf-8")


def load_warnings() -> dict[str, dict[str, list[dict[str, Any]]]]:
    ensure_data_files()
    with WARNINGS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else {}


def save_warnings(data: dict[str, dict[str, list[dict[str, Any]]]]) -> None:
    ensure_data_files()
    with WARNINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def add_warning(
    guild_id: int,
    member_id: int,
    moderator_id: int,
    reason: str,
) -> dict[str, str | int]:
    warnings_data = load_warnings()
    guild_key = str(guild_id)
    member_key = str(member_id)

    guild_warnings = warnings_data.setdefault(guild_key, {})
    member_warnings = guild_warnings.setdefault(member_key, [])

    warning_entry = {
        "case_id": len(member_warnings) + 1,
        "moderator_id": moderator_id,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    member_warnings.append(warning_entry)
    save_warnings(warnings_data)
    return warning_entry


def get_member_warnings(guild_id: int, member_id: int) -> list[dict[str, Any]]:
    warnings_data = load_warnings()
    return warnings_data.get(str(guild_id), {}).get(str(member_id), [])


def load_exiles() -> dict[str, dict[str, dict[str, Any]]]:
    ensure_data_files()
    with EXILES_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else {}


def save_exiles(data: dict[str, dict[str, dict[str, Any]]]) -> None:
    ensure_data_files()
    with EXILES_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def add_exile(
    guild_id: int,
    member_id: int,
    moderator_id: int,
    reason: str,
    duration_seconds: int,
) -> dict[str, Any]:
    exiles_data = load_exiles()
    guild_key = str(guild_id)
    member_key = str(member_id)
    now = datetime.now(timezone.utc)

    guild_exiles = exiles_data.setdefault(guild_key, {})
    exile_entry = {
        "member_id": member_id,
        "moderator_id": moderator_id,
        "reason": reason,
        "duration_seconds": duration_seconds,
        "started_at": now.isoformat(),
        "expires_at": (now.timestamp() + duration_seconds),
    }
    guild_exiles[member_key] = exile_entry
    save_exiles(exiles_data)
    return exile_entry


def get_member_exile(guild_id: int, member_id: int) -> dict[str, Any] | None:
    exiles_data = load_exiles()
    return exiles_data.get(str(guild_id), {}).get(str(member_id))


def clear_member_exile(guild_id: int, member_id: int) -> None:
    exiles_data = load_exiles()
    guild_key = str(guild_id)
    member_key = str(member_id)

    guild_exiles = exiles_data.get(guild_key, {})
    if member_key in guild_exiles:
        del guild_exiles[member_key]

    if not guild_exiles and guild_key in exiles_data:
        del exiles_data[guild_key]

    save_exiles(exiles_data)


def get_active_exiles() -> dict[str, dict[str, dict[str, Any]]]:
    return load_exiles()
