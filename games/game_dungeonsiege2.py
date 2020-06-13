# -*- encoding: utf-8 -*-

from PyQt5.QtCore import QFileInfo

import mobase

from ..basic_game import BasicGame


class DarkMessiahOfMightAndMagicGame(BasicGame):
    Name = "Dungeon Siege II"
    Author = "Holt59"
    Version = "0.1.0"

    GameName = "Dungeon Siege II"
    GameShortName = "dungeonsiegeii"
    GameNexusName = "dungeonsiegeii"
    GameNexusId = 2078
    GameSteamId = 39200
    GameBinary = "DungeonSiege2.exe"
    GameDataPath = ""

    GameDocumentsDirectory = "%DOCUMENTS%/My Games/Dungeon Siege 2"

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        return True

    def executables(self):
        execs = super().executables()
        execs.append(
            mobase.ExecutableInfo(
                "Dungeon Siege Video Configuration",
                QFileInfo(self.gameDirectory().absoluteFilePath("DS2VideoConfig.exe")),
            )
        )
        return execs

    def iniFiles(self):
        return ["DungeonSiege2.ini"]
