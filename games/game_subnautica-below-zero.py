from ..basic_game import BasicGame


class SubnauticaGame(BasicGame):

    Name = "Subnautica Below Zero Support Plugin"
    Author = "dekart811"
    Version = "1.0"

    GameName = "Subnautica: Below Zero"
    GameShortName = "subnauticabelowzero"
    GameNexusName = "subnauticabelowzero"
    GameSteamId = 848450
    GameBinary = "SubnauticaZero.exe"
    GameDataPath = "QMods"
    GameDocumentsDirectory = "%GAME_PATH%"
    GameSupportURL = r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/Game:-Subnautica:-Below-Zero"

    def iniFiles(self):
        return ["doorstop_config.ini"]
