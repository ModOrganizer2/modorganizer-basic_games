from ..basic_game import BasicGame
from ..basic_features import BasicGameSaveGameInfo

import mobase
import os

class XP11Game(BasicGame):

    Name = "X-Plane 11 Support Plugin"
    Author = "Deorder"
    Version = "0.0.1"

    GameName = "X-Plane 11"
    GameShortName = "xp11"
    GameBinary = r"X-Plane.exe"
    GameDataPath = r""