import os

from pathlib import Path
from PyQt5.QtCore import QDir, QFileInfo

import mobase

from ..basic_game import BasicGame


class GTA3DefinitiveEditionModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()

    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        for entry in tree:
            if Path(entry.name().casefold()).suffix == ".pak":
                return mobase.ModDataChecker.VALID

        return mobase.ModDataChecker.INVALID


class GTA3DefinitiveEditionGame(BasicGame):

    Name = "Grand Theft Auto III - Definitive Edition Support Plugin"
    Author = "dekart811"
    Version = "1.0"

    GameName = "GTA III - Definitive Edition"
    GameShortName = "grandtheftautothetrilogy"
    GameNexusName = "grandtheftautothetrilogy"
    GameBinary = "Gameface/Binaries/Win64/LibertyCity.exe"
    GameDataPath = "Gameface/Content/Paks/~mods"
    GameDocumentsDirectory = (
        "%USERPROFILE%/Documents/Rockstar Games/"
        "GTA III Definitive Edition/Config/WindowsNoEditor"
    )
    GameSavesDirectory = "%GAME_DOCUMENTS%/../../SaveGames"
    GameSaveExtension = "sav"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = GTA3DefinitiveEditionModDataChecker()
        return True

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
