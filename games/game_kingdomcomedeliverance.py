# -*- encoding: utf-8 -*-

import os

from PyQt5.QtCore import QDir

from ..basic_game import BasicGame


class KingdomComeDeliveranceGame(BasicGame):
    Name = "Kingdom Come Deliverance Support Plugin"
    Author = "Silencer711"
    Version = "1.0.0"

    GameName = "Kingdom Come: Deliverance"
    GameShortName = "kingdomcomedeliverance"
    GameNexusName = "kingdomcomedeliverance"
    GameNexusId = 2298
    GameSteamId = [379430]
    GameGogId = [1719198803]
    GameBinary = "bin/Win64/KingdomCome.exe"
    GameDataPath = "mods"
    GameSaveExtension = "whs"
    GameDocumentsDirectory = "%GAME_PATH%"
    GameSavesDirectory = "%USERPROFILE%/Saved Games/kingdomcome/saves"

    def iniFiles(self):
        return ["custom.cfg", "system.cfg", "user.cfg"]

    def initializeProfile(self, path: QDir, settings: int):
        # Create .cfg files if they don't exist
        for iniFile in self.iniFiles():
            iniPath = self.documentsDirectory().absoluteFilePath(iniFile)
            if not os.path.exists(iniPath):
                with open(iniPath, "w") as _:
                    pass

        # Create the mods directory if it doesn't exist
        modsPath = self.dataDirectory().absolutePath()
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)

        super().initializeProfile(path, settings)
