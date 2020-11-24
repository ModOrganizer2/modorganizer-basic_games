# -*- encoding: utf-8 -*-

from ..basic_game import BasicGame


class KingdomComeDeliveranceGame(BasicGame):
    Name = "Kingdom Come Deliverance Support Plugin"
    Author = "Silencer711"
    Version = "1.0.0"

    GameName = "Kingdom Come: Deliverance"
    GameShortName = "kingdomcomedeliverance"
    GameNexusName = "kingdomcomedeliverance"
    GameNexusId = 2298
    GameSteamId = [379430]
    GameGogId = [1719198803]
    GameBinary = "bin/Win64/KingdomCome.exe"
    GameDataPath = "mods"
    GameSaveExtension = "whs"
    GameDocumentsDirectory = "%GAME_PATH%"
    GameSavesDirectory = "%USERPROFILE%/Saved Games/kingdomcome/saves"

    def iniFiles(self):
        return ["custom.cfg, system.cfg, user.cfg"]
