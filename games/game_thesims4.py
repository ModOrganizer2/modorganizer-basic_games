# -*- encoding: utf-8 -*-

from pathlib import Path
from typing import List

from PyQt5.QtCore import QDir

import mobase

from ..basic_features import BasicGameSaveGameInfo
from ..basic_game import BasicGame, BasicGameSaveGame


# This doesn't seem to work yet, not sure why
class TheSims4ModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()

    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        for entry in tree:
            name = entry.name().casefold()
            if entry.isDir():
                continue
            if name.endswith((".ts4script", ".package")) and name.count("\\") == 1:
                return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.VALID


class TheSims4SaveGame(BasicGameSaveGame):
    def allFiles(self):
        return [self._filename, self._filename.replace(".save", ".png")]


class TheSims4Game(BasicGame):

    Name = "The Sims 4 Support Plugin"
    Author = "Lhyris"
    Version = "1.0.0"

    GameName = "The Sims 4"
    GameShortName = "thesims4"
    GaneNexusHame = "thesims4"
    GameNexusId = 641
    GameSteamId = [1222670]
    GameOriginManifestIds = ["OFB-EAST:109552299@steam", "SIMS4.OFF.SOLP.0x000000000001266C", "SIMS4.OFR.50.0000005"]
    GameBinary = "Game/Bin/TS4_x64.exe"
    GameDocumentsDirectory = "%DOCUMENTS%/Electronic Arts/The Sims 4"
    GameDataPath = "%GAME_DOCUMENTS%/Mods"
    GameSavesDirectory = "%GAME_DOCUMENTS%/saves"
    GameSaveExtension = "save"

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        self._featureMap[mobase.SaveGameInfo] = BasicGameSaveGameInfo(
            lambda s: s.replace(".save", ".png")
        )
        return True

    def iniFiles(self):
        return ["Options.ini"]

    def listSaves(self, folder: QDir) -> List[mobase.ISaveGame]:
        ext = self._mappings.savegameExtension.get()
        return [
            TheSims4SaveGame(path)
            for path in Path(folder.absolutePath()).glob(f"*.{ext}")
        ]
