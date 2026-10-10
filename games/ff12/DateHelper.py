from datetime import datetime


def get_date_time_from_iso(date_iso: str) -> str:
    """
    Convert ISO 8601 string to 'YYYY-MM-DD HH:MM UTC'.
    Return input if parsing fails or input is not a string.
    """
    if not isinstance(date_iso, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        return str(date_iso)
    try:
        dt = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return date_iso


def get_date_from_iso(date_iso: str) -> str:
    """
    Convert ISO 8601 string to 'YYYY-MM-DD'.
    Return input if parsing fails or input is not a string.
    """
    if not isinstance(date_iso, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        return str(date_iso)
    try:
        dt = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return date_iso
