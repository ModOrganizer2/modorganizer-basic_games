# -*- encoding: utf-8 -*-
import sys
import os
import winreg
import re

from PyQt5.QtCore import QFileInfo

import mobase

from ..basic_game import BasicGame
from ..basic_features import BasicGameSaveGameInfo

class Titanfall2(BasicGame):

    Name = "Titanfall 2 Support Plugin"
    Author = "Luca/EzioTheDeadPoet"
    Version = "1.0.0"
    Description = "Well I made this to easily share my Modded Titanfall 2 Setup and switch between Japanese and English"

    GameName = "Titanfall 2"
    GameShortName = "titanfall2"
    GaneNexusName = "titanfall2"
    GameNexusId = 2532
    #GameSteamId = 1237970
    GameBinary = "Titanfall2.exe"
    GameDataPath = ""
    GameSaveExtension = "sav"
    GameDocumentsDirectory = "%DOCUMENTS%/Respawn/Titanfall2"

    #def init(self, organizer: mobase.IOrganizer):
    #    super().init(organizer)
    #    return True

    def isInstalled(self):
        RawKey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Respawn\\Titanfall2")
        Key = winreg.QueryValueEx(RawKey, "Install Dir")
        winreg.CloseKey(RawKey)
        Dir = re.search("'(.*)'", str(Key))
        self.setGamePath(str(Dir[1]))
        return True
