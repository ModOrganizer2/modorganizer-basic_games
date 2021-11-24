from ..basic_game import BasicGame


class SubnauticaGame(BasicGame):

    Name = "Subnautica Support Plugin"
    Author = "dekart811"
    Version = "1.0"

    GameName = "Subnautica"
    GameShortName = "subnautica"
    GameNexusName = "subnautica"
    GameSteamId = 264710
    GameBinary = "Subnautica.exe"
    GameDataPath = "QMods"
    GameDocumentsDirectory = "%GAME_PATH%"

    def iniFiles(self):
        return ["doorstop_config.ini"]
