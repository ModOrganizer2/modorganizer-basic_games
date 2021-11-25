from PyQt5.QtCore import QDir
from ..basic_game import BasicGame

import mobase


class DA2Game(BasicGame):

    Name = "Dragon Age 2 Support Plugin"
    Author = "Patchier"

    GameName = "Dragon Age 2"
    GameShortName = "dragonage2"
    GameBinary = r"bin_ship\DragonAge2.exe"
    GameDataPath = r"%DOCUMENTS%\BioWare\Dragon Age 2\packages\core\override"
    GameSaveExtension = "das"
    GameSteamId = 1238040
    GameOriginManifestIds = ["OFB-EAST:59474", "DR:201797000"]
    GameOriginWatcherExecutables = ("DragonAge2.exe",)

    def version(self):
        # Don't forget to import mobase!
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.final)

    def savesDirectory(self):
        return QDir(self.documentsDirectory().absoluteFilePath("gamesaves"))
