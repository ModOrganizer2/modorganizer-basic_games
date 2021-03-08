from ..basic_game import BasicGame
from ..basic_features import BasicGameSaveGameInfo

import mobase
import os


class BeamNGGame(BasicGame):

    Name = "BeamNG.drive Support Plugin"
    Author = "Deorder"
    Version = "0.0.1"

    GameName = "BeamNG.drive"
    GameShortName = "beamng"
    GameBinary = r"Bin64\BeamNG.drive.x64.exe"
    GameDataPath = r"%DOCUMENTS%\BeamNG.drive"
    GameSteamId = [284160]
