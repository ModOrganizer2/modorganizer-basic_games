from PyQt6.QtCore import QFileInfo

import mobase

from ..basic_game import BasicGame


class RailworksGame(BasicGame):

    Name = "Train Simulator 20xx Support Plugin"
    Author = "Ryan Young"

    GameName = "Train Simulator"
    GameShortName = "railworks"
    GameBinary = "RailWorks.exe"
    GameValidShortNames = ["ts1"]
    GameDataPath = ""
    GameSteamId = "24010"

    def version(self):
        # Don't forget to import mobase!
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.final)

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Train Simulator (32-bit)",
                QFileInfo(self.gameDirectory(), "RailWorks.exe"),
            ),
            mobase.ExecutableInfo(
                "Train Simulator (64-bit)",
                QFileInfo(self.gameDirectory(), "RailWorks64.exe"),
            ),
        ]
