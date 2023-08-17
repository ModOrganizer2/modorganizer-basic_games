# -*- encoding: utf-8 -*-

import mobase
from typing import List, Optional
from ..basic_game import BasicGame

class DragonsDogmaDarkArisenModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()
    
    def dataLooksValid(self, tree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        folders: List[mobase.IFileTree] = []
        files: List[mobase.FileTreeEntry] = []

        for entry in tree:
            if isinstance(entry, mobase.IFileTree):
                folders.append(entry)
            else:
                files.append(entry)

        VALID_FOLDERS = [
            "movie",
            "rom",
            "sa",
            "sound",
            "system",
            "tgs",
            "usershader",
            "usertexture",
        ]
        
        VALID_FILE_EXTENSIONS = [
            ".arc",
        ]
        
        for src_folder in folders:
            for dst_folder in VALID_FOLDERS:
                if src_folder.name().lower() == dst_folder.lower():
                    return mobase.ModDataChecker.VALID
                    
        for src_file in files:
            for extension in VALID_FILE_EXTENSIONS:
                if src_file.name().lower().endswith(extension.lower()):
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