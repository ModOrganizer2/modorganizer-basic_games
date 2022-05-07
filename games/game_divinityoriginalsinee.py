# -*- encoding: utf-8 -*-

import os
from typing import List, Optional

import mobase

from ..basic_features import BasicGameSaveGameInfo
from ..basic_game import BasicGame


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
            DivinityOriginalSinEnhancedEditionGame.DOCS_MOD_SPECIAL_NAME,
        ]
        for src_folder in folders:
            for dst_folder in VALID_FOLDERS:
                if src_folder.name().lower() == dst_folder.lower():
                    return mobase.ModDataChecker.VALID

        VALID_FILE_EXTENSIONS = [
            ".pak",
        ]
        for src_file in files:
            for extension in VALID_FILE_EXTENSIONS:
                if src_file.name().lower().endswith(extension.lower()):
                    return mobase.ModDataChecker.VALID

        return mobase.ModDataChecker.INVALID

    def fix(self, tree: mobase.IFileTree) -> Optional[mobase.IFileTree]:
        return None


class DivinityOriginalSinEnhancedEditionGame(BasicGame, mobase.IPluginFileMapper):
    Name = "Divinity: Original Sin (Enhanced Edition) Support Plugin"
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
        "Divinity Original Sin Enhanced Edition"
    )
    GameSavesDirectory = (
        "%USERPROFILE%/Documents/Larian Studios/"
        "Divinity Original Sin Enhanced Edition/PlayerProfiles"
    )
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Divinity:-Original-Sin"
    )

    DOCS_MOD_SPECIAL_NAME = "DOCS_MOD"

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        self._featureMap[mobase.SaveGameInfo] = BasicGameSaveGameInfo(
            lambda s: s.with_suffix(".png")
        )
        self._featureMap[
            mobase.ModDataChecker
        ] = DivinityOriginalSinEnhancedEditionModDataChecker()
        return True

    def mappings(self) -> List[mobase.Mapping]:
        map = []
        modDirs = [self.DOCS_MOD_SPECIAL_NAME]
        self._listDirsRecursive(modDirs, prefix=self.DOCS_MOD_SPECIAL_NAME)
        for dir_ in modDirs:
            for file_ in self._organizer.findFiles(path=dir_, filter=lambda x: True):
                m = mobase.Mapping()
                m.createTarget = True
                m.isDirectory = False
                m.source = file_
                m.destination = os.path.join(
                    self.documentsDirectory().absoluteFilePath("Mods"),
                    file_.split(self.DOCS_MOD_SPECIAL_NAME)[1].strip("\\").strip("/"),
                )
                map.append(m)
        return map

    def primarySources(self):
        return self.GameValidShortNames

    def _listDirsRecursive(self, dirs_list, prefix=""):
        dirs = self._organizer.listDirectories(prefix)
        for dir_ in dirs:
            dir_ = os.path.join(prefix, dir_)
            dirs_list.append(dir_)
            self._listDirsRecursive(dirs_list, dir_)
