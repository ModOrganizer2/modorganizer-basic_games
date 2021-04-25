# -*- encoding: utf-8 -*-

from typing import List, Optional

import mobase

from ..basic_game import BasicGame
from ..basic_features import BasicGameSaveGameInfo


class DivinityOriginalSinEnhancedEditionModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()

    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:

        folders: List[mobase.IFileTree] = []
        files: List[mobase.FileTreeEntry] = []

        for entry in tree:
            if isinstance(entry, mobase.IFileTree):
                folders.append(entry)
            else:
                files.append(entry)

        VALID_FOLDERS = [
            "Cursors",
            "DLC",
            "Engine",
            "Fonts",
            "Localization",
            "PakInfo",
            "PlayerProfiles",
            "Public",
            "Shaders",
        ]
        for src_folder in folders:
            for dst_folder in VALID_FOLDERS:
                if src_folder.name().lower() == dst_folder.lower():
                    return mobase.ModDataChecker.VALID

        return mobase.ModDataChecker.INVALID

    def fix(self, tree: mobase.IFileTree) -> Optional[mobase.IFileTree]:
        return None


class DivinityOriginalSinEnhancedEditionGame(BasicGame):
    Name = "Divinity Original Sin Enhanced Edition Support Plugin"
    Author = "LostDragonist"
    Version = "1.0.0"

    GameName = "Divinity: Original Sin (Enhanced Edition)"
    GameShortName = "divinityoriginalsinenhancededition"
    GameNexusName = "divinityoriginalsinenhancededition"
    GameValidShortNames = ["divinityoriginalsin"]
    GameNexusId = 1995
    GameSteamId = [373420]
    GameGogId = [1445516929, 1445524575]
    GameBinary = "Shipping/EoCApp.exe"
    GameDataPath = "Data"
    GameSaveExtension = "lsv"
    GameDocumentsDirectory = (
        "%USERPROFILE%/Documents/Larian Studios/"
        "Divinity Original Sin Enhanced Edition/PlayerProfiles"
    )
    GameSavesDirectory = (
        "%USERPROFILE%/Documents/Larian Studios/"
        "Divinity Original Sin Enhanced Edition/PlayerProfiles"
    )

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        self._featureMap[mobase.SaveGameInfo] = BasicGameSaveGameInfo(
            lambda s: s.replace(".lsv", ".png")
        )
        self._featureMap[
            mobase.ModDataChecker
        ] = DivinityOriginalSinEnhancedEditionModDataChecker()
        return True
