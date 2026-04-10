import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
NOTES_FILE = DATA_DIR / "notes.json"


def _ensure() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not NOTES_FILE.exists():
        NOTES_FILE.write_text("{}", encoding="utf-8")


def _load() -> dict[str, Any]:
    _ensure()
    data = json.loads(NOTES_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _save(data: dict[str, Any]) -> None:
    _ensure()
    NOTES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def add_note(guild_id: int, member_id: int, author_id: int, content: str) -> dict[str, Any]:
    data = _load()
    member_notes = data.setdefault(str(guild_id), {}).setdefault(str(member_id), [])
    note = {
        "note_id": max((int(n["note_id"]) for n in member_notes), default=0) + 1,
        "author_id": author_id,
        "content": content[:500],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    member_notes.append(note)
    _save(data)
    return note


def get_member_notes(guild_id: int, member_id: int) -> list[dict[str, Any]]:
    return _load().get(str(guild_id), {}).get(str(member_id), [])


def remove_note(guild_id: int, member_id: int, note_id: int) -> dict[str, Any] | None:
    data = _load()
    guild_key, member_key = str(guild_id), str(member_id)
    member_notes = data.get(guild_key, {}).get(member_key, [])
    for i, note in enumerate(member_notes):
        if int(note["note_id"]) == note_id:
            removed = member_notes.pop(i)
            if not member_notes:
                data.get(guild_key, {}).pop(member_key, None)
            _save(data)
            return removed
    return None
