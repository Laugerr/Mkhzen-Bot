import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DECREES_FILE = DATA_DIR / "decrees.json"
APPEALS_FILE = DATA_DIR / "appeals.json"
VOTES_FILE = DATA_DIR / "votes.json"


def _ensure() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    for f in (DECREES_FILE, APPEALS_FILE, VOTES_FILE):
        if not f.exists():
            f.write_text("{}", encoding="utf-8")


def _load(path: Path) -> dict[str, Any]:
    _ensure()
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _save(path: Path, data: dict[str, Any]) -> None:
    _ensure()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ─── DECREES ─────────────────────────────────────────────────────────────────

def add_decree(guild_id: int, author_id: int, title: str, content: str) -> dict[str, Any]:
    data = _load(DECREES_FILE)
    decrees = data.setdefault(str(guild_id), [])
    decree = {
        "decree_id": max((int(d["decree_id"]) for d in decrees), default=0) + 1,
        "author_id": author_id,
        "title": title[:100],
        "content": content[:1500],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }
    decrees.append(decree)
    _save(DECREES_FILE, data)
    return decree


def get_decrees(guild_id: int) -> list[dict[str, Any]]:
    return _load(DECREES_FILE).get(str(guild_id), [])


def repeal_decree(guild_id: int, decree_id: int) -> dict[str, Any] | None:
    data = _load(DECREES_FILE)
    for decree in data.get(str(guild_id), []):
        if int(decree["decree_id"]) == decree_id and decree["status"] == "active":
            decree["status"] = "repealed"
            decree["repealed_at"] = datetime.now(timezone.utc).isoformat()
            _save(DECREES_FILE, data)
            return decree
    return None


# ─── APPEALS ─────────────────────────────────────────────────────────────────

def add_appeal(guild_id: int, member_id: int, reason: str) -> dict[str, Any]:
    data = _load(APPEALS_FILE)
    appeals = data.setdefault(str(guild_id), [])
    appeal = {
        "appeal_id": max((int(a["appeal_id"]) for a in appeals), default=0) + 1,
        "member_id": member_id,
        "reason": reason[:1000],
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_by": None,
        "resolved_at": None,
        "resolution_note": None,
    }
    appeals.append(appeal)
    _save(APPEALS_FILE, data)
    return appeal


def get_appeals(guild_id: int, status: str | None = None) -> list[dict[str, Any]]:
    appeals = _load(APPEALS_FILE).get(str(guild_id), [])
    return [a for a in appeals if a["status"] == status] if status else appeals


def resolve_appeal(guild_id: int, appeal_id: int, resolver_id: int, note: str) -> dict[str, Any] | None:
    data = _load(APPEALS_FILE)
    for appeal in data.get(str(guild_id), []):
        if int(appeal["appeal_id"]) == appeal_id and appeal["status"] == "open":
            appeal["status"] = "resolved"
            appeal["resolved_by"] = resolver_id
            appeal["resolved_at"] = datetime.now(timezone.utc).isoformat()
            appeal["resolution_note"] = note[:500]
            _save(APPEALS_FILE, data)
            return appeal
    return None


# ─── VOTES ───────────────────────────────────────────────────────────────────

def add_vote(
    guild_id: int,
    author_id: int,
    question: str,
    duration_seconds: int,
    channel_id: int,
    message_id: int,
) -> dict[str, Any]:
    data = _load(VOTES_FILE)
    guild_votes = data.setdefault(str(guild_id), {})
    vote_id = max((int(k) for k in guild_votes), default=0) + 1
    now = datetime.now(timezone.utc)
    vote = {
        "vote_id": vote_id,
        "author_id": author_id,
        "question": question[:200],
        "yes_votes": [],
        "no_votes": [],
        "created_at": now.isoformat(),
        "ends_at": now.timestamp() + duration_seconds,
        "channel_id": channel_id,
        "message_id": message_id,
        "status": "active",
    }
    guild_votes[str(vote_id)] = vote
    _save(VOTES_FILE, data)
    return vote


def get_vote(guild_id: int, vote_id: int) -> dict[str, Any] | None:
    return _load(VOTES_FILE).get(str(guild_id), {}).get(str(vote_id))


def cast_vote(guild_id: int, vote_id: int, member_id: int, choice: str) -> bool:
    """Record a yes/no vote. Returns False if already voted or vote is closed."""
    data = _load(VOTES_FILE)
    vote = data.get(str(guild_id), {}).get(str(vote_id))
    if not vote or vote["status"] != "active":
        return False
    member_str = str(member_id)
    if member_str in vote["yes_votes"] or member_str in vote["no_votes"]:
        return False
    vote["yes_votes" if choice == "yes" else "no_votes"].append(member_str)
    _save(VOTES_FILE, data)
    return True


def close_vote(guild_id: int, vote_id: int) -> dict[str, Any] | None:
    data = _load(VOTES_FILE)
    vote = data.get(str(guild_id), {}).get(str(vote_id))
    if vote:
        vote["status"] = "closed"
        _save(VOTES_FILE, data)
    return vote


def get_all_active_votes() -> dict[str, list[dict[str, Any]]]:
    data = _load(VOTES_FILE)
    result: dict[str, list[dict[str, Any]]] = {}
    for guild_id, guild_votes in data.items():
        active = [v for v in guild_votes.values() if v["status"] == "active"]
        if active:
            result[guild_id] = active
    return result
