import json
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtCore import QDir

import mobase

from ..basic_features import BasicLocalSavegames
from ..basic_features.basic_save_game_info import (
    BasicGameSaveGame,
    BasicGameSaveGameInfo,
)
from ..basic_game import BasicGame


class DaggerfallUnityModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()
        self.validDirNames = [
            "biogs",
            "docs",
            "factions",
            "fonts",
            "mods",
            "questpacks",
            "quests",
            "sound",
            "soundfonts",
            "spellicons",
            "tables",
            "text",
            "textures",
            "worlddata",
            "aa",
        ]

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        for entry in filetree:
            if not entry.isDir():
                continue
            if entry.name().casefold() in self.validDirNames:
                return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.INVALID


class DaggerfallSaveGame(BasicGameSaveGame):
    def __init__(self, filepath: Path):
        super().__init__(filepath)
        self.saveInfo = json.loads(open(self._filepath / "SaveInfo.txt", "r").read())

    def getName(self) -> str:
        return f"[{self.saveInfo['characterName']}] {self.saveInfo['saveName']}"

    def getFilepath(self):
        return self._filepath.as_posix()

    def allFiles(self):
        return list(map(str, self._filepath.glob("*")))


def parse_daggerfall_save_metadata(save_path: Path, save: mobase.ISaveGame):
    saveInfo = json.loads(open(save_path / "SaveInfo.txt", "r").read())
    saveData = json.loads(open(save_path / "SaveData.txt", "r").read())

    epoch = datetime(1, 1, 1)
    save_time = epoch + timedelta(microseconds=saveInfo["dateAndTime"]["realTime"] / 10)

    return {
        "Save Name": saveInfo["saveName"],
        "Character Name": saveInfo["characterName"],
        "Level": saveData["playerData"]["playerEntity"]["level"],
        "Gender": saveData["playerData"]["playerEntity"]["gender"],
        "Race": saveData["playerData"]["playerEntity"]["raceTemplate"]["Name"],
        "Reflexes": saveData["playerData"]["playerEntity"]["reflexes"],
        "Date": save_time.strftime("%Y-%m-%d %H:%M:%S"),
    }


class DaggerfallUnityGame(BasicGame):
    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(DaggerfallUnityModDataChecker())
        self._register_feature(BasicLocalSavegames(self))
        self._register_feature(
            BasicGameSaveGameInfo(
                lambda p: Path(p or "", "Screenshot.jpg"),
                parse_daggerfall_save_metadata,
            )
        )
        return True

    Name = "Daggerfall Unity Support Plugin"
    Author = "HomerSimpleton & Oknehsorod"
    Version = "1.0.1"

    GameName = "Daggerfall Unity"
    GameShortName = "daggerfallunity"
    GameBinary = "DaggerfallUnity.exe"
    GameLauncher = "DaggerfallUnity.exe"
    GameDataPath = "%GAME_PATH%/DaggerfallUnity_Data/StreamingAssets"
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Daggerfall-Unity"
    )
    GameSavesDirectory = (
        r"%USERPROFILE%/AppData/LocalLow/Daggerfall Workshop/Daggerfall Unity/Saves"
    )

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        save_games = super().listSaves(folder)
        path = Path(folder.absolutePath())
        save_games.extend(DaggerfallSaveGame(f) for f in path.glob("SAVE*"))
        return save_games
