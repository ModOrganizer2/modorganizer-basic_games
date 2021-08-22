# -*- encoding: utf-8 -*-

# Code greatly inspired by https://github.com/LostDragonist/steam-library-setup-tool

import sys
import winreg  # type: ignore
from pathlib import Path
from typing import Dict, List, Optional

import vdf


class SteamGame:
    def __init__(self, appid, installdir):
        self.appid = appid
        self.installdir = installdir

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{} ({})".format(self.appid, self.installdir)


class LibraryFolder:
    def __init__(self, path: Path):
        self.path = path

        self.games = []
        for filepath in path.joinpath("steamapps").glob("appmanifest_*.acf"):
            try:
                with open(filepath, "r", encoding="utf-8") as fp:
                    info = vdf.load(fp)
                    app_state = info["AppState"]
            except KeyError:
                print(
                    f'Unable to read application state from "{filepath}"',
                    file=sys.stderr,
                )
                continue
            except Exception as e:
                print(f'Unable to parse file "{filepath}": {e}', file=sys.stderr)
                continue

            try:
                app_id = app_state["appid"]
                install_dir = app_state["installdir"]
                self.games.append(SteamGame(app_id, install_dir))
            except KeyError:
                print(
                    f"Unable to read application ID or installation folder "
                    f'from "{filepath}"',
                    file=sys.stderr,
                )
                continue

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "LibraryFolder at {}: {}".format(self.path, self.games)


def parse_library_info(library_vdf_path: Path) -> List[LibraryFolder]:
    """
    Read library folders from the main library file.

    Args:
        library_vdf_path: The main library file (from the Steam installation
            folder).

    Returns:
        A list of LibraryFolder, for each library found.
    """

    with open(library_vdf_path, "r", encoding="utf-8") as f:
        info = vdf.load(f)

    library_folders = []

    if "libraryfolders" in info:
        # new format
        info_folders = info["libraryfolders"]

        def get_path(value):
            return value["path"]

    elif "LibraryFolders" in info:
        # old format
        info_folders = info["LibraryFolders"]

        def get_path(value):
            return value

    else:
        raise ValueError(f'Unknown file format from "{library_vdf_path}"')

    for key, value in info_folders.items():
        # only keys that are integer values contains library folder
        try:
            int(key)
        except ValueError:
            continue

        path = get_path(value)
        try:
            library_folders.append(LibraryFolder(Path(path)))
        except Exception as e:
            print(
                'Failed to read steam library from "{}", {}'.format(path, repr(e)),
                file=sys.stderr,
            )

    return library_folders


def find_steam_path() -> Optional[Path]:
    """
    Retrieve the Steam path, if available.

    Returns:
        The Steam path, or None if Steam is not installed.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Valve\\Steam") as key:
            value = winreg.QueryValueEx(key, "SteamExe")
            return Path(value[0].replace("/", "\\")).parent
    except FileNotFoundError:
        return None


def find_games() -> Dict[str, Path]:
    """
    Find the list of Steam games installed.

    Returns:
        A mapping from Steam game ID to install locations for available
        Steam games.
    """
    steam_path = find_steam_path()
    if not steam_path:
        return {}

    library_vdf_path = steam_path.joinpath("steamapps", "libraryfolders.vdf")

    try:
        library_folders = parse_library_info(library_vdf_path)
        library_folders.append(LibraryFolder(steam_path))
    except FileNotFoundError:
        return {}

    games: Dict[str, Path] = {}
    for library in library_folders:
        for game in library.games:
            games[game.appid] = Path(library.path).joinpath(
                "steamapps", "common", game.installdir
            )

    return games


if __name__ == "__main__":
    games = find_games()
    for k, v in games.items():
        print("Found game with id {} at {}.".format(k, v))
