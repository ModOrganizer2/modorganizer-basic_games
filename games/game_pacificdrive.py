import mobase
from PyQt6.QtCore import QDir

from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_game import BasicGame


class PacificDriveGame(BasicGame):
    Name = "Pacific Drive Support Plugin"
    Author = "AlixTechie"
    Version = "1.0.0"

    GameName = "Pacific Drive"
    GameShortName = "pacificdrive"
    GameNexusName = "pacificdrive"
    GameNexusId = 6169
    GameEpicId = "d6d8a7241f6841a8823f5a533a1564da"
    GameSteamId = 1458140

    GameBinary = "PenDriverPro.exe"
    GameValidShortNames = ["pendriverpro"]
    GameDataPath = "%GAME_PATH%/PenDriverPro/Content/Paks/"
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Pacific-Drive"
    )
    GameSavesDirectory = "%USERPROFILE%/AppData/Local/PenDriverPro"
    GameSaveExtension = "sav"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(BasicModDataChecker(GlobPatterns(valid=["*.pak"])))
        return True
