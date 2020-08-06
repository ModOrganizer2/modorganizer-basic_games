# -*- encoding: utf-8 -*-

# Code greatly inspired by https://github.com/LostDragonist/steam-library-setup-tool

import os
import winreg  # type: ignore

from pathlib import Path
from typing import Dict


class SteamGame:
    def __init__(self, appid, installdir):
        self.appid = appid
        self.installdir = installdir

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{} ({})".format(self.appid, self.installdir)


class LibraryFolder:
    def __init__(self, path: str):
        self.path = path

        self.games = []
        for filename in os.listdir(os.path.join(path, "steamapps")):
            if filename.startswith("appmanifest"):
                with open(
                    os.path.join(path, "steamapps", filename), "r", encoding="utf-8"
                ) as fp:
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

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "LibraryFolder at {}: {}".format(self.path, self.games)


def parse_library_info(library_vdf_path):

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
                    library_folders.append(
                        LibraryFolder(parts[2].strip().replace("\\\\", "\\"))
                    )
                except (FileNotFoundError, ValueError):
                    continue

    return library_folders


def find_games() -> Dict[str, Path]:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Valve\\Steam") as key:
            value = winreg.QueryValueEx(key, "SteamExe")
            steam_path = value[0].replace("/", "\\")
    except FileNotFoundError:
        return {}

    library_vdf_path = os.path.join(
        os.path.dirname(steam_path), "steamapps", "libraryfolders.vdf"
    )

    library_folders = parse_library_info(library_vdf_path)
    library_folders.append(LibraryFolder(os.path.dirname(steam_path)))

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
