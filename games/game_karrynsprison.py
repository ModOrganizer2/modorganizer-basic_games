# -*- encoding: utf-8 -*-
from pathlib import Path
from typing import List
from PyQt5.QtCore import QDir

import mobase

from ..basic_game import BasicGameSaveGame, BasicGame


class KarrynsPrisonSaveGame(BasicGameSaveGame):
    name = "";

    def __init__(self, filepath: Path):
        super().__init__(filepath)
        self.name = filepath.stem

    def getName(self) -> str:
        return super().getName() if self.name == "" else self.name


class KarrynsPrisonModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()
        self.validDirNames = [
            "www",
        ]

    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        for entry in tree:
            if entry.name().casefold() in self.validDirNames:
                return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.INVALID


class KarrynsPrisonGame(BasicGame):
    Name = "Karryn's Prison Plugin"
    Author = "madtisa"
    Version = "1.1.0"

    GameName = "Karryn's Prison"
    GameShortName = "karrynsprison"
    GameSteamId = 1619750
    GameBinary = "nw.exe"
    GameDataPath = ""
    GameSavesDirectory = "%GAME_PATH%/www/save"
    GameSaveExtension = "rpgsave"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = KarrynsPrisonModDataChecker()
        return True

    def listSaves(self, folder: QDir) -> List[mobase.ISaveGame]:
        profiles = []
        for path in Path(folder.absolutePath()).glob("file*"):
            profiles.append(KarrynsPrisonSaveGame(path))

        return profiles
