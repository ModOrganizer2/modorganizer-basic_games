import json
from pathlib import Path

import mobase
from PyQt6.QtCore import QDir

from ..basic_features import BasicLocalSavegames
from ..basic_features.basic_save_game_info import (
    BasicGameSaveGame,
    BasicGameSaveGameInfo,
    format_date,
)
from ..basic_game import BasicGame


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
        return True

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        ext = self._mappings.savegameExtension.get()
        return [
            CyberpunkSaveGame(path.parent)
            for path in Path(folder.absolutePath()).glob(f"**/*.{ext}")
        ]

    def iniFiles(self):
        return ["UserSettings.json"]
