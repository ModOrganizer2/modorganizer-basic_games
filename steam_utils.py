# -*- encoding: utf-8 -*-

# Code greatly inspired by https://github.com/LostDragonist/steam-library-setup-tool

import sys
import winreg  # type: ignore

from pathlib import Path
from typing import Dict, List, Optional


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
        for filepath in path.joinpath("steamapps").iterdir():
            if filepath.name.startswith("appmanifest") and filepath.is_file():
                try:
                    with open(filepath, "r", encoding="utf-8") as fp:
                        i, n = None, None
                        for line in fp:
                            line = line.strip()

                            if line.startswith('"appid"'):
                                i = line.replace('"appid"', "").strip()[1:-1]
                            if line.startswith('"installdir"'):
                                n = line.replace('"installdir"', "").strip()[1:-1]

                            if i is not None and n is not None:
                                break
                    if i is None or n is None:
                        continue
                    self.games.append(SteamGame(i, n))
                except UnicodeDecodeError:
                    print('Unable to parse file "{}"'.format(filepath), file=sys.stderr)

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

    library_folders = []

    with open(library_vdf_path, "r") as f:

        # Find the line containing "LibraryFolders" (quoted):
        it = iter(f)
        for line in it:

            line = line.strip().strip('"')
            if line == "LibraryFolders":
                break

        # Find the opening {:
        for line in it:
            if line.strip() == "{":
                break

        # Read the folders:
        for line in it:
            line = line.strip()
            if line == "}":
                break

            # Strip " on each side and split, we should get
            # 3 parts with an empty middle
            parts = line.strip('"').split('"')

            if len(parts) == 3 and not parts[1].strip():
                try:
                    int(parts[0].strip())
                except ValueError:
                    continue

                try:
                    path = parts[2].strip().replace("\\\\", "\\")
                    library_folders.append(LibraryFolder(Path(path)))
                except Exception as e:
                    print(
                        'Failed to read steam library from "{}", {}'.format(
                            path, repr(e)
                        ),
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
