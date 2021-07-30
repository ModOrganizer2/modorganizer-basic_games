# -*- encoding: utf-8 -*-

import mobase
from PyQt5.QtCore import QFileInfo
from ..basic_game import BasicGame
from typing import List


class StarWarsEmpireAtWarGame(BasicGame):
    Name = "STAR WARS Empire at War"
    Author = "erri120"
    Version = "1.0.0"

    GameName = "STAR WARS™ Empire at War"
    GameShortName = "starwarsempireatwar"
    GameNexusName = "starwarsempireatwar"
    GameNexusId = 453
    GameSteamId = 32470
    GameGogId = 1421404887
    # using StarWarsG.exe instead of sweaw.exe because it has an icon
    GameBinary = "GameData/StarWarsG.exe"
    GameDataPath = "GameData/Data"

    def executables(self) -> List[mobase.ExecutableInfo]:
        return [
            mobase.ExecutableInfo(
                "STAR WARS Empire at War",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            )
        ]
