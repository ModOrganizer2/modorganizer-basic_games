import os

from PyQt5.QtCore import QDir
from PyQt5.QtCore import QFileInfo

from typing import List, Optional

import mobase

from ..basic_game import BasicGame

class GTA3DefinitiveEditionGame(BasicGame):

    Name = "Grand Theft Auto III - Definitive Edition Support Plugin"
    Author = "dekart811"
    Version = "1.0"

    GameName = "GTA III - Definitive Edition"
    GameShortName = "grandtheftautothetrilogy"
    GameNexusHame = "grandtheftautothetrilogy"
    GameBinary = "Gameface/Binaries/Win64/LibertyCity.exe"
    GameDataPath = "Gameface/Content/Paks/~mods"
    GameDocumentsDirectory = "%USERPROFILE%/Documents/Rockstar Games/GTA III Definitive Edition/Config/WindowsNoEditor"
    GameSavesDirectory = "%GAME_DOCUMENTS%/../../SaveGames"
    GameSaveExtension = "sav"

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "GTA III - Definitive Edition",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
            mobase.ExecutableInfo(
                "GTA III - Definitive Edition (DirectX 12)",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ).withArgument("-dx12"),
        ]

    def iniFiles(self):
        return ["GameUserSettings.ini", "CustomSettings.ini"]

    def initializeProfile(self, path: QDir, settings: int):
        # Create the mods directory if it doesn't exist
        modsPath = self.dataDirectory().absolutePath()
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)

        super().initializeProfile(path, settings)