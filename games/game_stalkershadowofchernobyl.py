from PyQt5.QtCore import QDir, QStandardPaths

import mobase

from ..basic_game import BasicGame


class StalkerShocGame(BasicGame):
    Name = "S.T.A.L.K.E.R.: Shadow of Chernobyl Support Plugin"
    Author = "lowtied"
    Version = "0.1.0"

    GameName = "S.T.A.L.K.E.R.: Shadow of Chernobyl"
    GameShortName = "stalkershadowofchernobyl"
    GameNexusName = "stalkershadowofchernobyl"

    GameNexusId = 1428
    GameSteamId = 4500
    GameGogId = 1207660573

    GameBinary = "bin/XR_3DA.exe"
    GameDataPath = ""

    GameSaveExtension = "sav"
    GameSavesDirectory = "%GAME_DOCUMENTS%/savedgames"

    def documentsDirectory(self) -> QDir:
        fsgame = self.gameDirectory().absoluteFilePath("fsgame.ltx")
        if self.is_steam():
            return QDir(self.gameDirectory().absoluteFilePath("_appdata_"))

        documents = QDir(
            QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        )
        return QDir(documents.absoluteFilePath("stalker-shoc"))

    def savesDirectory(self) -> QDir:
        return QDir(self.documentsDirectory().absoluteFilePath("savedgames"))


# vim: ft=python sw=4 ts=4 sts=-1 sta et
