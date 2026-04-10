def parse_duration(duration_text: str) -> int:
    """Parse a duration string like '10m', '2h', '1d' into seconds."""
    units = {"m": 60, "h": 3600, "d": 86400}
    if len(duration_text) < 2:
        raise ValueError("Duration must look like `10m`, `2h`, or `1d`.")
    unit = duration_text[-1].lower()
    value_text = duration_text[:-1]
    if unit not in units or not value_text.isdigit():
        raise ValueError("Duration must look like `10m`, `2h`, or `1d`.")
    value = int(value_text)
    if value <= 0:
        raise ValueError("Duration must be greater than zero.")
    return value * units[unit]


def format_duration(duration_seconds: int) -> str:
    """Format a duration in seconds to a human-readable string like '1d 2h 30m'."""
    days, remainder = divmod(duration_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts)
