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

    def iniFiles(self):
        return ["doorstop_config.ini"]
