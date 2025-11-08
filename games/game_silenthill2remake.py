from ..basic_game import BasicGame
import mobase

class SilentHill2RemakeModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()
        self.validDirNames = [
            "."
        ]

    def dataLooksValid(self, filetree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        for entry in filetree:
            if not entry.isDir():
                continue
            if entry.name().casefold() in (name.casefold() for name in self.validDirNames):
                return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.INVALID

class SilentHill2RemakeGame(BasicGame):
    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(SilentHill2RemakeModDataChecker())
        return True

    Name = "Silent Hill 2 Remake Support Plugin"
    Author = "HomerSimpleton Returns"
    Version = "1.0"

    GameName = "Silent Hill 2 Remake"
    GameShortName = "silenthill2"
    GameNexusName = "silenthill2"

    GameBinary = "SHProto/Binaries/Win64/SHProto-Win64-Shipping.exe"
    GameLauncher = "SHProto.exe"
    #GameDataPath = "%GAME_PATH%/SHProto/Content/Paks/~mods"
    GameDataPath = "%GAME_PATH%/SHProto/Content"
    GameSupportURL = "https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/Game:-Silent-Hill-2-Remake"

    GameGogId = [1225972913, 2051029707]

    # def executables(self):
    #     return [
    #         {
    #             "name": "Silent Hill 2 Remake",
    #             "binary": self.GameBinary,
    #         }
    #     ]

    # def dataDirectory(self):
    #     return self._gamePath + "/SHProto/Content/Paks"
