from ..basic_game import BasicGame


class Fallout76Game(BasicGame):

    Name = "Fallout 76 Support Plugin"
    Author = "TDarkShadow"
    Version = "1.0.1"

    GameName = "Fallout 76"
    GameShortName = "f76"
    GameBinary = "Fallout76.exe"
    GameDataPath = "%GAME_PATH%/Data"
    GameDocumentsDirectory = "%DOCUMENTS%/My Games/Fallout 76"
    GameSteamId = 1151340
    GameNexusId = 2590
    GameNexusName = "fallout76"

    def iniFiles(self):
        return ["Fallout76.ini, Fallout76Prefs.ini, Fallout76Custom.ini"]
