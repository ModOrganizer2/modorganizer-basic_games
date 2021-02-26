# -*- encoding: utf-8 -*-

from PyQt5.QtCore import QFileInfo

import mobase

from ..basic_game import BasicGame


class NoMansSkyGame(BasicGame):

    Name = "No Man's Sky Support Plugin"
    Author = "Luca/EzioTheDeadPoet"
    Version = "1.0.0"

    GameName = "No Man's Sky"
    GameShortName = "nomanssky"
    GameNexusName = "nomanssky"
    GameNexusId = 1634
    GameSteamId = 275850
    GameGogId = 1446213994
    GameBinary = "Binaries/NMS.exe"
    GameDataPath = "GAMEDATA/PCBANKS/MODS"

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "No Man's Sky",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
            mobase.ExecutableInfo(
                "No Man's Sky VR",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ).withArgument("-HmdEnable 1"),
        ]
