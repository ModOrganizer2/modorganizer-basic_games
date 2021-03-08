from ..basic_game import BasicGame
from ..basic_features import BasicGameSaveGameInfo

import mobase
import os


class AssettoCorsaGame(BasicGame):

    Name = "Assetto Corsa Support Plugin"
    Author = "Deorder"
    Version = "0.0.1"

    GameName = "Assetto Corsa"
    GameShortName = "ac"
    GameBinary = r"AssettoCorsa.exe"
    GameDataPath = r""
    GameSteamId = 244210
    GameDocumentsDirectory = "%DOCUMENTS%/Assetto Corsa"

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        return True
