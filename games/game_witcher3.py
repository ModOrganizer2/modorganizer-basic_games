# -*- encoding: utf-8 -*-
import sys
import os
import winreg
import re

import mobase


from ..basic_game import BasicGame
from ..basic_features import BasicGameSaveGameInfo


class Witcher3Game(BasicGame):

    Name = "Witcher 3 Support Plugin"
    Author = "Holt59 & Luca/EzioTheDeadPoet"
    Version = "1.1.0"
    Description = "A plugin to make the Witcher work with Mod Organizer 2"

    GameName = "The Witcher 3: Wild Hunt"
    GameShortName = "witcher3"
    GaneNexusHame = "witcher3"
    GameNexusId = 952
    GameSteamId = 292030
    GameBinary = "bin/x64/witcher3.exe"
    GameDataPath = ""
    GameSaveExtension = "sav"
    GameDocumentsDirectory = "%DOCUMENTS%/The Witcher 3"
    GameSavesDirectory = "%GAME_DOCUMENTS%/gamesaves"

    # GOG Compatibility
    
    def isInstalled(self):
        if super().isInstalled():
            return True
        try:
            RawKey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\GOG.com\\Games\\1495134320")
            Key = winreg.QueryValueEx(RawKey, "path")
            winreg.CloseKey(RawKey)
            Dir = re.search("'(.*)'", str(Key))
            self.setGamePath(str(Dir[1]))
            return True
        except:
            return False

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        self._featureMap[mobase.SaveGameInfo] = BasicGameSaveGameInfo(
            lambda s: s.replace(".sav", ".png")
        )
        return True
