from __future__ import annotations

import dataclasses
import os
from pathlib import Path

from PyQt5.QtCore import QDir

import mobase

from ..basic_features.basic_mod_data_checker import BasicModDataChecker
from ..basic_features.basic_save_game_info import (
    BasicGameSaveGame,
    BasicGameSaveGameInfo,
)
from ..basic_game import BasicGame
from .game_subnautica import subnautica_file_patterns

subnautica_below_zero_file_patterns = dataclasses.replace(
    subnautica_file_patterns, set_as_root={"BepInExPack_BelowZero"}
)


class SubnauticaGame(BasicGame):

    Name = "Subnautica Below Zero Support Plugin"
    Author = "dekart811, Zash"
    Version = "2.0"

    GameName = "Subnautica: Below Zero"
    GameShortName = "subnauticabelowzero"
    GameNexusName = "subnauticabelowzero"
    GameSteamId = 848450
    GameBinary = "SubnauticaZero.exe"
    GameDataPath = ""
    GameDocumentsDirectory = "%GAME_PATH%"
    GameSavesDirectory = r"%GAME_PATH%\SNAppData\SavedGames"

    _forced_libraries = ["winhttp.dll"]

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = BasicModDataChecker(
            subnautica_below_zero_file_patterns
        )
        self._featureMap[mobase.SaveGameInfo] = BasicGameSaveGameInfo(
            lambda s: os.path.join(s, "screenshot.jpg")
        )
        return True

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        savegames = super().listSaves(folder)
        for save_path in [
            folder.absolutePath(),
            os.path.expandvars(
                r"%USERPROFILE%\Appdata\LocalLow\Unknown Worlds"
                r"\Subnautica Below Zero\SubnauticaZero\SavedGames"
            ),
        ]:
            savegames.extend(
                BasicGameSaveGame(folder) for folder in Path(save_path).glob("slot*")
            )
        return savegames

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        return [
            mobase.ExecutableForcedLoadSetting(self.binaryName(), lib).withEnabled(True)
            for lib in self._forced_libraries
        ]
