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

    next_id = max((int(w["case_id"]) for w in member_warnings), default=0) + 1
    warning_entry = {
        "case_id": next_id,
        "moderator_id": moderator_id,
        "reason": reason[:500],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    member_warnings.append(warning_entry)
    save_warnings(warnings_data)
    return warning_entry


def get_member_warnings(guild_id: int, member_id: int) -> list[dict[str, Any]]:
    warnings_data = load_warnings()
    return warnings_data.get(str(guild_id), {}).get(str(member_id), [])


def remove_member_warning(guild_id: int, member_id: int, case_id: int) -> dict[str, Any] | None:
    warnings_data = load_warnings()
    guild_key = str(guild_id)
    member_key = str(member_id)

    member_warnings = warnings_data.get(guild_key, {}).get(member_key, [])
    removed_warning: dict[str, Any] | None = None

    for index, warning in enumerate(member_warnings):
        if int(warning.get("case_id", 0)) == case_id:
            removed_warning = member_warnings.pop(index)
            break

    if removed_warning is None:
        return None

    if not member_warnings:
        warnings_data.get(guild_key, {}).pop(member_key, None)
        if not warnings_data.get(guild_key):
            warnings_data.pop(guild_key, None)

    save_warnings(warnings_data)
    return removed_warning


def clear_member_warnings(guild_id: int, member_id: int) -> int:
    warnings_data = load_warnings()
    guild_key = str(guild_id)
    member_key = str(member_id)

    member_warnings = warnings_data.get(guild_key, {}).get(member_key, [])
    removed_count = len(member_warnings)
    if removed_count == 0:
        return 0

    warnings_data[guild_key].pop(member_key, None)
    if not warnings_data[guild_key]:
        warnings_data.pop(guild_key, None)

    save_warnings(warnings_data)
    return removed_count


def _normalize_exile_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"active": {}, "history": {}}

    active = data.get("active")
    history = data.get("history")

    if isinstance(active, dict) and isinstance(history, dict):
        return {"active": active, "history": history}

    return {"active": data if isinstance(data, dict) else {}, "history": {}}


def load_exiles() -> dict[str, Any]:
    ensure_data_files()
    with EXILES_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return _normalize_exile_data(data)


def save_exiles(data: dict[str, Any]) -> None:
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

    active_exiles = exiles_data.setdefault("active", {})
    history_exiles = exiles_data.setdefault("history", {})

    guild_exiles = active_exiles.setdefault(guild_key, {})
    guild_history = history_exiles.setdefault(guild_key, {})
    member_history = guild_history.setdefault(member_key, [])

    exile_entry = {
        "case_id": max((int(e["case_id"]) for e in member_history), default=0) + 1,
        "member_id": member_id,
        "moderator_id": moderator_id,
        "reason": reason[:500],
        "duration_seconds": duration_seconds,
        "started_at": now.isoformat(),
        "expires_at": (now.timestamp() + duration_seconds),
        "status": "active",
        "resolved_at": None,
        "resolution": None,
    }
    guild_exiles[member_key] = exile_entry
    member_history.append(dict(exile_entry))
    save_exiles(exiles_data)
    return exile_entry


def get_member_exile(guild_id: int, member_id: int) -> dict[str, Any] | None:
    exiles_data = load_exiles()
    return exiles_data.get("active", {}).get(str(guild_id), {}).get(str(member_id))


def clear_member_exile(guild_id: int, member_id: int, resolution: str | None = None) -> dict[str, Any] | None:
    exiles_data = load_exiles()
    guild_key = str(guild_id)
    member_key = str(member_id)

    active_exiles = exiles_data.get("active", {})
    history_exiles = exiles_data.get("history", {})

    guild_exiles = active_exiles.get(guild_key, {})
    removed_entry = guild_exiles.get(member_key)
    if member_key in guild_exiles:
        del guild_exiles[member_key]

    if removed_entry is not None:
        history_entry_list = history_exiles.get(guild_key, {}).get(member_key, [])
        if history_entry_list:
            latest_entry = history_entry_list[-1]
            latest_entry["status"] = "resolved"
            latest_entry["resolved_at"] = datetime.now(timezone.utc).isoformat()
            latest_entry["resolution"] = resolution

    if not guild_exiles and guild_key in active_exiles:
        del active_exiles[guild_key]

    save_exiles(exiles_data)
    return removed_entry


def get_active_exiles() -> dict[str, dict[str, dict[str, Any]]]:
    return load_exiles().get("active", {})


def get_member_exile_history(guild_id: int, member_id: int) -> list[dict[str, Any]]:
    exiles_data = load_exiles()
    return exiles_data.get("history", {}).get(str(guild_id), {}).get(str(member_id), [])
