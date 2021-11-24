import os

from PyQt5.QtCore import QDir
from PyQt5.QtCore import QFileInfo

from typing import List, Optional

import mobase

from ..basic_game import BasicGame

class GTASanAndreasDefinitiveEditionGame(BasicGame):

    Name = "Grand Theft Auto: San Andreas - Definitive Edition Support Plugin"
    Author = "dekart811"
    Version = "1.0"

    GameName = "GTA: San Andreas - Definitive Edition"
    GameShortName = "grandtheftautothetrilogy"
    GameNexusHame = "grandtheftautothetrilogy"
    GameBinary = "Gameface/Binaries/Win64/SanAndreas.exe"
    GameDataPath = "Gameface/Content/Paks/~mods"
    GameDocumentsDirectory = "%USERPROFILE%/Documents/Rockstar Games/GTA San Andreas Definitive Edition/Config/WindowsNoEditor"
    GameSavesDirectory = "%GAME_DOCUMENTS%/../../SaveGames"
    GameSaveExtension = "sav"

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "GTA: San Andreas - Definitive Edition",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
            mobase.ExecutableInfo(
                "GTA: San Andreas - Definitive Edition (DirectX 12)",
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