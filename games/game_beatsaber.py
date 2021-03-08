from ..basic_game import BasicGame
from ..basic_features import BasicGameSaveGameInfo

import mobase
import os

class BeatSaberGame(BasicGame):

    Name = "Beat Saber Support Plugin"
    Author = "Deorder"
    Version = "0.0.1"

    GameName = "Beat Saber"
    GameShortName = "beatsaber"
    GameBinary = r"Beat Saber.exe"
    GameDataPath = r""
    GameSteamId = [620980]
