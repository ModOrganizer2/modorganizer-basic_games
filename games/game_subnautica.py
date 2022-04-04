from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtCore import QDir

import mobase

from ..basic_features import BasicModDataChecker
from ..basic_features.basic_save_game_info import (
    BasicGameSaveGame,
    BasicGameSaveGameInfo,
)
from ..basic_game import BasicGame


class SubnauticaModDataChecker(BasicModDataChecker):
    default_file_patterns = {
        "unfold": ["BepInExPack_Subnautica"],
        "valid": ["winhttp.dll", "doorstop_config.ini", "BepInEx", "QMods"],
        "delete": [
            "*.txt",
            "*.md",
            "icon.png",
            "license",
            "manifest.json",
        ],
        "move": {"plugins": "BepInEx/", "patchers": "BepInEx/", "*": "QMods/"},
    }


class SubnauticaGame(BasicGame):

    Name = "Subnautica Support Plugin"
    Author = "dekart811, Zash"
    Version = "2.0"

    GameName = "Subnautica"
    GameShortName = "subnautica"
    GameNexusName = "subnautica"
    GameSteamId = 264710
    GameEpicId = "Jaguar"
    GameBinary = "Subnautica.exe"
    GameDataPath = ""
    GameDocumentsDirectory = "%GAME_PATH%"
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Subnautica"
    )
    GameSavesDirectory = r"%GAME_PATH%\SNAppData\SavedGames"

    _game_extra_save_paths = [
        r"%USERPROFILE%\Appdata\LocalLow\Unknown Worlds"
        r"\Subnautica\Subnautica\SavedGames"
    ]

    _forced_libraries = ["winhttp.dll"]

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = SubnauticaModDataChecker()
        self._featureMap[mobase.SaveGameInfo] = BasicGameSaveGameInfo(
            lambda s: os.path.join(s, "screenshot.jpg")
        )
        return True

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        return [
            BasicGameSaveGame(folder)
            for save_path in (
                folder.absolutePath(),
                *(os.path.expandvars(p) for p in self._game_extra_save_paths),
            )
            for folder in Path(save_path).glob("slot*")
        ]

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        return [
            mobase.ExecutableForcedLoadSetting(self.binaryName(), lib).withEnabled(True)
            for lib in self._forced_libraries
        ]
