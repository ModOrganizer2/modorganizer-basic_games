
from PyQt6.QtCore import QFileInfo
import mobase
from ..basic_game import BasicGame

class FLiMLModContentChecker(modbase.ModDataChecker):
    def __init__(self):
        super().__init__()

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        for e in filetree:
            if isinstance(e, mobase.IFileTree) and e.exists(
                "mod.json", mobase.IFileTree.FILE
            ):
                return mobase.ModDataChecker.VALID
            
        return mobase.ModDataChecker.INVALID

class FantasyLifeI(BasicGame):
    Name = "Fantasy Life I Support Plugin"
    Author = "AmeliaCute"
    Version = "0.2.0"

    GameName = "Fantasy Life i: The Girl who Steals Time"
    GameShortName = "fantasylifei"
    GameNexusName = "fantasylifeithegirlwhostealstime"
    GameValidShortNames = ["fli"]

    GameBinary = "Game/Binaries/Win64/NFL1-Win64-Shipping.exe"
    GameLauncher = "NFL1.exe"

    GameSteamId = 2993780
    GameDataPath = "Mods"

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        self._register_feature(FLiMLModContentChecker)
        return True
    
    def executables(self):
        return [
            mobase.ExecutableInfo(
               "Fantasy Life i", QFileInfo(self.gameDirectory(), "Game/Binaries/Win64/NFL1-Win64-Shipping.exe") 
            ),
        ]

