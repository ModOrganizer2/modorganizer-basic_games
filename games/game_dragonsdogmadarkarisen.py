# -*- encoding: utf-8 -*-

import os
import mobase
from typing import List, Optional
from ..basic_game import BasicGame

class DragonsDogmaDarkArisenModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()
        
    valid_root_folder = False
    valid_arc_found = False
        
    def checkEntry(self, path: str, entry: mobase.FileTreeEntry) -> mobase.IFileTree.WalkReturn:
        # we check to see if an .arc file is contained within a valid root folder
        VALID_FOLDERS = ["rom", ]
        VALID_FILE_EXTENSIONS = [ ".arc", ]

        pathRoot = path.split(os.sep)[0]
        
        for extension in VALID_FILE_EXTENSIONS:
            if entry.name().lower().endswith(extension.lower()):
                self.valid_arc_found = True
                if pathRoot.lower() in VALID_FOLDERS:
                    self.valid_root_folder = True
                    return mobase.IFileTree.WalkReturn.STOP

        return mobase.IFileTree.WalkReturn.CONTINUE

    def dataLooksValid(self, tree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        self.valid_root_folder = False
        self.valid_arc_found = False

        tree.walk(self.checkEntry, os.sep)
        
        if (self.valid_root_folder == True):
            if (self.valid_arc_found == True):
                return mobase.ModDataChecker.VALID

        return mobase.ModDataChecker.INVALID


class DragonsDogmaDarkArisen(BasicGame):

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = DragonsDogmaDarkArisenModDataChecker()
        return True

    Name = "Dragon's Dogma: Dark Arisen Support Plugin"
    Author = "Luca/EzioTheDeadPoet/MikoMuto"
    Version = "1.1.0"

    GameName = "Dragon's Dogma: Dark Arisen"
    GameShortName = "dragonsdogma"
    GaneNexusHame = "dragonsdogma"
    GameSteamId = 367500
    GameGogId = 1242384383
    GameBinary = "DDDA.exe"
    GameDataPath = "nativePC"
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Dragon's-Dogma:-Dark-Arisen"
    )
    