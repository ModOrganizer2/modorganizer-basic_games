# -*- encoding: utf-8 -*-

from PyQt5.QtCore import QDir, QFileInfo, QStandardPaths

import mobase

from ..basic_game import BasicGame


class StardewValleyGame(BasicGame):
    Name = "StardewValley"
    Author = "Syer10"
    Version = "0.1.0a"

    GameName = "Stardew Valley"
    GameShortName = "stardewvalley"
    GameNexusName = "stardewvalley"
    GameNexusId = 1303
    GameSteamId = 413150
    GameBinary = "Stardew Valley.exe"
    GameDataPath = "mods"

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "SMAPI", QFileInfo(self.gameDirectory(), "StardewModdingAPI.exe")
            ),
            mobase.ExecutableInfo(
                "Stardew Valley", QFileInfo(self.gameDirectory(), "Stardew Valley.exe")
            ),
        ]

    def documentsDirectory(self):
        return QDir(
            "{}/StardewValley".format(
                QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
            )
        )

    def savesDirectory(self):
        return QDir(self.documentsDirectory().absoluteFilePath("Saves"))
