import os

import mobase

from ..basic_features import BasicGameSaveGameInfo
from ..basic_game import BasicGame


class DAOriginsGame(BasicGame):

    Name = "Dragon Age Origins Support Plugin"
    Author = "Patchier"
    Version = "1.1.0"

    GameName = "Dragon Age: Origins"
    GameShortName = "dragonage"
    GameBinary = r"bin_ship\DAOrigins.exe"
    GameDataPath = r"%DOCUMENTS%\BioWare\Dragon Age\packages\core\override"
    GameSavesDirectory = r"%DOCUMENTS%\BioWare\Dragon Age\Characters"
    GameSaveExtension = "das"
    GameSteamId = [17450, 47810]
    GameGogId = 1949616134

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        self._featureMap[mobase.SaveGameInfo] = BasicGameSaveGameInfo(
            lambda s: os.path.split(s)[0] + "/screen.dds"
        )
        return True
