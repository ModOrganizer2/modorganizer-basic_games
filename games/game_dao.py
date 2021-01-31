from PyQt5.QtCore import QDir
from ..basic_game import BasicGame

import mobase


class DAOriginsGame(BasicGame):

    Name = "Dragon Age Origins Support Plugin"
    Author = "Patchier"

    GameName = "Dragon Age: Origins"
    GameShortName = "dragonage"
    GameBinary = r"bin_ship\DAOrigins.exe"
    GameDataPath = r"%DOCUMENTS%\BioWare\Dragon Age\packages\core\override"
    GameSaveExtension = "das"
    GameSteamId = [17450, 47810]
    GameGogId = 1949616134

    def version(self):
        # Don't forget to import mobase!
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.final)

    def savesDirectory(self):
        return QDir(self.documentsDirectory().absoluteFilePath("gamesaves"))
