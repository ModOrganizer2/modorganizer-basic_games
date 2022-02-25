# -*- encoding: utf-8 -*-

from PyQt5.QtCore import QFileInfo, QDir

import mobase

from ..basic_game import BasicGame


class MasterDuelGame(BasicGame):

    Name = "Yu-Gi-Oh! Master Duel Support Plugin"
    Author = "The Conceptionist & uwx"
    Version = "1.0.1"
    Description = "Adds support for basic Yu-Gi-Oh! Master Duel mods.\nCurrently does not support any mods that require modifying the masterduel_Data/StreamingAssets folder."

    GameName = "Yu-Gi-Oh! Master Duel"
    GameShortName = "masterduel"
    GameNexusName = "yugiohmasterduel"
    GameNexusId = 4272
    GameSteamId = 1449850
    GameBinary = "masterduel.exe"

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Yu-Gi-Oh! Master Duel",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ).withArgument("-popupwindow"),
        ]
    
    def dataDirectory(self) -> QDir:
        localData = QDir(self.gameDirectory().absoluteFilePath('LocalData'))
        subdirs = localData.entryList(filters=(QDir.Dirs | QDir.NoDotAndDotDot))
        return QDir(QDir.toNativeSeparators(localData.absoluteFilePath(subdirs[0]) + '/0000'))