import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PRESTIGE_FILE = DATA_DIR / "prestige.json"


def _ensure() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not PRESTIGE_FILE.exists():
        PRESTIGE_FILE.write_text("{}", encoding="utf-8")


def _load() -> dict[str, Any]:
    _ensure()
    data = json.loads(PRESTIGE_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _save(data: dict[str, Any]) -> None:
    _ensure()
    PRESTIGE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _blank() -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "prestige": 0,
        "daily_xp": 0,
        "daily_reset": now,
        "last_active": now,
        "honour_total": 0,
    }


def get_member_prestige(guild_id: int, member_id: int) -> dict[str, Any]:
    return _load().get(str(guild_id), {}).get(str(member_id), _blank())


def add_message_xp(guild_id: int, member_id: int, amount: int, daily_cap: int) -> int:
    """Award XP from a message. Returns XP actually granted (0 if daily cap hit)."""
    data = _load()
    entry = data.setdefault(str(guild_id), {}).setdefault(str(member_id), _blank())
    now = datetime.now(timezone.utc)

    try:
        reset_time = datetime.fromisoformat(entry["daily_reset"])
    except (ValueError, KeyError):
        reset_time = now - timedelta(days=1)

    if (now - reset_time).total_seconds() >= 86400:
        entry["daily_xp"] = 0
        entry["daily_reset"] = now.isoformat()

    entry["last_active"] = now.isoformat()

    if entry["daily_xp"] >= daily_cap:
        _save(data)
        return 0

    awarded = min(amount, daily_cap - entry["daily_xp"])
    entry["prestige"] += awarded
    entry["daily_xp"] += awarded
    _save(data)
    return awarded


def add_honour(guild_id: int, member_id: int, amount: int) -> dict[str, Any]:
    """Add staff-granted honour. No daily cap. Amount may be negative."""
    data = _load()
    entry = data.setdefault(str(guild_id), {}).setdefault(str(member_id), _blank())
    entry["prestige"] = max(0, entry["prestige"] + amount)
    entry["honour_total"] = max(0, entry.get("honour_total", 0) + amount)
    entry["last_active"] = datetime.now(timezone.utc).isoformat()
    _save(data)
    return entry


def reset_prestige_partial(guild_id: int, member_id: int, fraction: float = 0.5) -> int:
    """Reduce prestige by a fraction. Used on demotion. Returns new value."""
    data = _load()
    entry = data.get(str(guild_id), {}).get(str(member_id))
    if entry is None:
        return 0
    entry["prestige"] = max(0, int(entry["prestige"] * (1.0 - fraction)))
    _save(data)
    return entry["prestige"]


def apply_decay(guild_id: int, decay_inactive_days: int, decay_amount: int) -> int:
    """Decay prestige for inactive members. Returns count of members affected."""
    data = _load()
    guild_data = data.get(str(guild_id), {})
    now = datetime.now(timezone.utc)
    decayed = 0

    for entry in guild_data.values():
        try:
            last_active = datetime.fromisoformat(entry["last_active"])
        except (ValueError, KeyError):
            continue
        if (now - last_active).days >= decay_inactive_days and entry.get("prestige", 0) > 0:
            entry["prestige"] = max(0, entry["prestige"] - decay_amount)
            decayed += 1

    if decayed:
        _save(data)
    return decayed


def get_guild_leaderboard(guild_id: int, limit: int = 10) -> list[tuple[int, dict[str, Any]]]:
    """Returns [(member_id, entry), ...] sorted by prestige descending."""
    guild_data = _load().get(str(guild_id), {})
    return sorted(
        ((int(k), v) for k, v in guild_data.items()),
        key=lambda x: x[1].get("prestige", 0),
        reverse=True,
    )[:limit]
