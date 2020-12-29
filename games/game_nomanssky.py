# -*- encoding: utf-8 -*-

from ..basic_game import BasicGame


class NoMansSkyGame(BasicGame):

    Name = "Mo Man's Sky Support Plugin"
    Author = "Luca/EzioTheDeadPoet"
    Version = "1.0.0"

    GameName = "Mo Man's Sky"
    GameShortName = "nomanssky"
    GaneNexusHame = "nomanssky"
    GameSteamId = 275850
    GameGogId = 1446213994
    GameBinary = "Binaries/NMS.exe"
    GameDataPath = "GAMEDATA/PCBANKS/MODS"

    def executables(self):
    return [
        mobase.ExecutableInfo(
            "No Man's Sky",
            QFileInfo(self.gameDirectory(), "Binaries/NMS.exe"),
        ),
    ]