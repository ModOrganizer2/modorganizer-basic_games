import vdf

from ...steam_utils import find_steam_path


def get_last_logged_steam_id() -> str | None:
    """
    Retrieve the Steam ID of the most recently logged-in user from Steam's loginusers.vdf.
    """
    steam_path = find_steam_path()
    if steam_path is None:
        return None

    loginusers_path = steam_path / "config" / "loginusers.vdf"
    try:
        with open(loginusers_path, "r", encoding="utf-8") as f:
            data = vdf.load(f)

        users = data.get("users", {})
        for steam_id, info in users.items():
            if info.get("MostRecent") == "1":
                return steam_id

        return next(iter(users), None)
    except Exception:
        return None
