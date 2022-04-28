import mobase

from ..basic_game import BasicGame


class TS4Game(BasicGame):

    Name = "The Sims 4 Support Plugin"
    Author = "R3z Shark"

    GameName = "The Sims 4"
    GameShortName = "thesims4"
    GameBinary = "Game/Bin/TS4_x64.exe"
    GameDataPath = "%DOCUMENTS%/Electronic Arts/The Sims 4/Mods"
    GameSteamId = 1222670
    GameOriginManifestIds = ["OFB-EAST:109552677"]
    GameOriginWatcherExecutables = ("TS4_x64.exe",)

    def version(self):
        # Don't forget to import mobase!
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.final)
