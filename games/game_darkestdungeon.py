# -*- encoding: utf-8 -*-

from PyQt5.QtCore import QDir, QFileInfo, QStandardPaths

import mobase

from ..basic_game import BasicGame


class DarkestDungeonGame(BasicGame):
    Name = "DarkestDungeon"
    Author = "erri120"
    Version = "0.1.0"

    GameName = "Darkest Dungeon"
    GameShortName = "darkestdungeon"
    GameNexusName = "darkestdungeon"
    GameNexusId = 804
    GameSteamId = 262060
    GameBinary = "_windows//darkest.exe"
    GameDataPath = ""

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Darkest Dungeon",
                QFileInfo(self.gameDirectory(), "_windows//darkest.exe"),
            ),
        ]

    def savesDirectory(self):
        return QDir(
            "{}/Darkest".format(
                QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
            )
        )
