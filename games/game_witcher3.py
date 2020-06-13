# -*- encoding: utf-8 -*-

import mobase


from ..basic_game import BasicGame
from ..basic_features import BasicGameSaveGameInfo


class Witcher3Game(BasicGame):

    Name = "Witcher 3 Support Plugin"
    Author = "Holt59"
    Version = "1.0.0a"
    Description = "The Description Of The Dead"

    GameName = "The Witcher 3: Wild Hunt"
    GameShortName = "witcher3"
    GaneNexusHame = "witcher3"
    GameNexusId = 952
    GameSteamId = 292030
    GameBinary = "bin/x64/witcher3.exe"
    GameDataPath = "Mods"
    GameSaveExtension = "sav"
    GameDocumentsDirectory = "%DOCUMENTS%/The Witcher 3"
    GameSavesDirectory = "%GAME_DOCUMENTS%/gamesaves"

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        self._featureMap[mobase.SaveGameInfo] = BasicGameSaveGameInfo(
            lambda s: s.replace(".sav", ".png")
        )
        return True
