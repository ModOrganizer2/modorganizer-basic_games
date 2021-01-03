# -*- encoding: utf-8 -*-

from PyQt5.QtCore import QDir, QFileInfo, QStandardPaths

import mobase

from ..basic_game import BasicGame


class DarkestDungeonGame(BasicGame):
    Name = "DarkestDungeon"
    Author = "erri120"
    Version = "0.1.1"

    GameName = "Darkest Dungeon"
    GameShortName = "darkestdungeon"
    GameNexusName = "darkestdungeon"
    GameNexusId = 804
    GameSteamId = 262060
    GameGogId = 1719198803
    GameBinary = "_windowsnosteam//darkest.exe"
    GameDataPath = ""

    def executables(self):
        path = QFileInfo(self.gameDirectory(), "_windows/darkest.exe")
        if not path.exists():
            path = QFileInfo(self.gameDirectory(), "_windowsnosteam/darkest.exe")
        return [
            mobase.ExecutableInfo("Darkest Dungeon", path),
        ]

    def savesDirectory(self):
        return QDir(
            "{}/Darkest".format(
                QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
            )
        )
