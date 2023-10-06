import json
import re
from pathlib import Path

import mobase
from PyQt6.QtCore import QDir

from ..basic_features import BasicLocalSavegames, BasicModDataChecker, GlobPatterns
from ..basic_features.basic_save_game_info import (
    BasicGameSaveGame,
    BasicGameSaveGameInfo,
    format_date,
)
from ..basic_features.utils import is_directory
from ..basic_game import BasicGame


class CyberpunkModDataChecker(BasicModDataChecker):
    def __init__(self):
        super().__init__(
            GlobPatterns(
                valid=[
                    "archive",
                    # redscript
                    "engine",
                    "r6",
                    "mods",  # RedMod
                    "red4ext",  # red4ext/RED4ext.dll is moved to root in .fix()
                    "bin",  # CET etc. gets handled below
                    "root",  # RootBuilder: hardlink / copy to game root
                ],
                move={
                    # archive and ArchiveXL
                    "*.archive": "archive/pc/mod/",
                    "*.xl": "archive/pc/mod/",
                },
            )
        )

    _extra_files_to_move = {
        # Red4ext: only .dll files
        "red4ext/RED4ext.dll": "root/red4ext/",
        "bin/x64/winmm.dll": "root/bin/x64/",
        # CET: all files, folder gets handled in .fix()
        "bin/x64/version.dll": "root/bin/x64/",
        "bin/x64/global.ini": "root/bin/x64/",
        "bin/x64/plugins/cyber_engine_tweaks.asi": "root/bin/x64/plugins/",
    }
    """Some frameworks need to be copied or hard linked to root. Use / as sep!"""
    _ignore_pattern = re.compile(r"licenses?$", re.I)

    _cet_path = "bin/x64/plugins/cyber_engine_tweaks/"

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        # fix: single root folders get traversed by Simple Installer
        parent = filetree.parent()
        if parent is not None and self.dataLooksValid(parent) is self.FIXABLE:
            return self.FIXABLE
        if (status := super().dataLooksValid(filetree)) is not self.INVALID:
            match self._check_bin_folder(filetree):
                case self.INVALID:
                    return self.INVALID
                case self.FIXABLE:
                    status = self.FIXABLE
                case _:
                    pass  # valid = keep status
            # Check extra fixes
            if any(filetree.exists(p) for p in self._extra_files_to_move):
                status = self.FIXABLE
        return status

    def _check_bin_folder(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        """Only Red4ext and CET are supported in bin folder."""
        bin_folder = filetree.find("bin/x64")
        if not bin_folder:
            return self.VALID
        elif not is_directory(bin_folder):
            return self.INVALID
        status = self.VALID
        cet_path = self._cet_path.rstrip("/\\")
        for entry in bin_folder:
            entry_name = entry.name()
            if self._ignore_pattern.match(entry_name):
                continue
            elif f"bin/x64/{entry_name}" in self._extra_files_to_move:
                status = self.FIXABLE
            elif entry_name == "plugins" and is_directory(entry):
                for plugin in entry:
                    plugin_path = f"bin/x64/plugins/{plugin.name()}"
                    if plugin_path == cet_path:
                        if not is_directory(plugin):
                            return self.INVALID
                        if not (len(plugin) == 1 and plugin.exists("mods")):
                            status = self.FIXABLE  # CET framework: fix
                    elif plugin_path in self._extra_files_to_move:
                        status = self.FIXABLE
                    else:
                        return self.INVALID  # unknown plugin
            else:
                return self.INVALID  # unknown entry
        return status

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        if filetree := super().fix(filetree):
            for source, target in self._extra_files_to_move.items():
                if file := filetree.find(source):
                    parent = file.parent()
                    filetree.move(file, target)
                    clear_empty_folder(parent)
            self._fix_cet_framework(filetree)
        return filetree

    def _fix_cet_framework(self, filetree: mobase.IFileTree):
        """Move CET framework to `root/`, except for `mods`.
        Only CET >= v1.27.0 (Patch 2.01) works with USVFS.

        See: https://github.com/maximegmd/CyberEngineTweaks/pull/877
        """
        if cet_folder := filetree.find(
            self._cet_path, mobase.FileTreeEntry.FileTypes.DIRECTORY
        ):
            assert is_directory(cet_folder)
            root_cet_path = f"root/{self._cet_path}"
            if not cet_folder.exists("mods"):
                parent = cet_folder.parent()
                filetree.move(cet_folder, root_cet_path.rstrip("/\\"))
            else:
                parent = cet_folder
                for entry in list(cet_folder):
                    if entry.name() != "mods":
                        filetree.move(entry, root_cet_path)
            clear_empty_folder(parent)


def clear_empty_folder(filetree: mobase.IFileTree | None):
    if filetree is None:
        return
    while not filetree:
        parent = filetree.parent()
        filetree.detach()
        if parent is None:
            break
        filetree = parent


def time_from_seconds(s: int | float) -> str:
    m, s = divmod(int(s), 60)
    h, m = divmod(int(m), 60)
    return f"{h:02}:{m:02}:{s:02}"


def parse_cyberpunk_save_metadata(save_path: Path, save: mobase.ISaveGame):
    metadata_file = save_path / "metadata.9.json"
    try:
        with open(metadata_file) as file:
            meta_data = json.load(file)["Data"]["metadata"]
            name = meta_data["name"]
            if name != (save_name := save.getName()):
                name = f"{save_name}  ({name})"
            return {
                "Name": name,
                "Date": format_date(meta_data["timestampString"], "hh:mm:ss, d.M.yyyy"),
                "Play Time": time_from_seconds(meta_data["playthroughTime"]),
                "Quest": meta_data["trackedQuestEntry"],
                "Level": int(meta_data["level"]),
                "Street Cred": int(meta_data["streetCred"]),
                "Life Path": meta_data["lifePath"],
                "Difficulty": meta_data["difficulty"],
                "Gender": f'{meta_data["bodyGender"]} / {meta_data["brainGender"]}',
                "Game version": meta_data["buildPatch"],
            }
    except (FileNotFoundError, json.JSONDecodeError):
        return None


class CyberpunkSaveGame(BasicGameSaveGame):
    _name_file = "NamedSave.txt"  # from mod: Named Saves

    def __init__(self, filepath: Path):
        super().__init__(filepath)
        try:  # Custom name from Named Saves
            with open(filepath / self._name_file) as file:
                self._name = file.readline()
        except FileNotFoundError:
            self._name = ""

    def getName(self) -> str:
        return self._name or super().getName()


class Cyberpunk2077Game(BasicGame):
    Name = "Cyberpunk 2077 Support Plugin"
    Author = "6788, Zash"
    Version = "1.4.0"

    GameName = "Cyberpunk 2077"
    GameShortName = "cyberpunk2077"
    GameBinary = "bin/x64/Cyberpunk2077.exe"
    GameLauncher = "REDprelauncher.exe"
    GameDataPath = "%GAME_PATH%"
    GameDocumentsDirectory = "%USERPROFILE%/AppData/Local/CD Projekt Red/Cyberpunk 2077"
    GameSavesDirectory = "%USERPROFILE%/Saved Games/CD Projekt Red/Cyberpunk 2077"
    GameSaveExtension = "dat"
    GameSteamId = 1091500
    GameGogId = 1423049311
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Cyberpunk-2077"
    )

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._featureMap[mobase.LocalSavegames] = BasicLocalSavegames(
            self.savesDirectory()
        )
        self._featureMap[mobase.SaveGameInfo] = BasicGameSaveGameInfo(
            lambda p: Path(p or "", "screenshot.png"),
            parse_cyberpunk_save_metadata,
        )
        self._featureMap[mobase.ModDataChecker] = CyberpunkModDataChecker()
        return True

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        ext = self._mappings.savegameExtension.get()
        return [
            CyberpunkSaveGame(path.parent)
            for path in Path(folder.absolutePath()).glob(f"**/*.{ext}")
        ]

    def iniFiles(self):
        return ["UserSettings.json"]
