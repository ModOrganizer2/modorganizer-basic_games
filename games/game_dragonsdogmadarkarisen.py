# -*- encoding: utf-8 -*-

import os
import re
import mobase
from pathlib import Path
from typing import List, Optional
from ..basic_game import BasicGame

from PyQt5.QtCore import QDir, QFileInfo, QStandardPaths

from ..basic_game import BasicGame, BasicGameSaveGame
from ..steam_utils import find_steam_path

class DragonsDogmaDarkArisenModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()
        
    ValidFileStructure = False
    FixableFileStructure = False
    re_bodycheck = re.compile('[fm]_[aiw]_\w+.arc')
        
    def checkEntry(self, path: str, entry: mobase.FileTreeEntry) -> mobase.IFileTree.WalkReturn:
        # we check to see if an .arc file is contained within a valid root folder
        VALID_FOLDERS = ["rom", ]
        VALID_FILE_EXTENSIONS = [ ".arc", ".stm", ".tex", ".qct" ]

        pathRoot = path.split(os.sep)[0]
        entryExt = entry.suffix().lower()
        re_check = re.compile('[0-9a-fA-F]{8}')
        
        echeck = re_check.match(entry.name())

        for extension in VALID_FILE_EXTENSIONS:
            if entry.name().lower().endswith(extension.lower()):
                if pathRoot.lower() in VALID_FOLDERS:
                    self.ValidFileStructure = True
                    return mobase.IFileTree.WalkReturn.STOP

        return mobase.IFileTree.WalkReturn.CONTINUE

    def dataLooksValid(self, tree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        self.ValidFileStructure = False
        self.FixableFileStructure = False
        
        #start with checking root folder for loose files
        for entry in tree:
            isBodyFile = self.re_bodycheck.match(entry.name())
            if isBodyFile:
                return mobase.ModDataChecker.FIXABLE
        
        #check subfolders if needed
        tree.walk(self.checkEntry, os.sep)
        
        if (self.FixableFileStructure == True):
                return mobase.ModDataChecker.FIXABLE
        if (self.ValidFileStructure == True):
                return mobase.ModDataChecker.VALID

        return mobase.ModDataChecker.INVALID
        
    def fix(self, tree: mobase.IFileTree) -> mobase.IFileTree:
        myBodies = []
        noSub = ["a_acc", "i_body", "w_leg"]
        for entry in tree:
            if not entry.isDir():
                isBodyFile = self.re_bodycheck.match(entry.name())
                if isBodyFile:
                    myBodies.append(entry)
                    
        if myBodies:
            for body in myBodies:
                parentFolder = str(body.name())[0]
                grandParentFolder = re.split(r'_(?=._)|[0-9]',str(body.name()))[1]
                if grandParentFolder in noSub:
                    rfolder = tree.addDirectory("rom").addDirectory("eq").addDirectory(grandParentFolder)
                else:
                    rfolder = tree.addDirectory("rom").addDirectory("eq").addDirectory(grandParentFolder).addDirectory(parentFolder)
                rfolder.insert(body, mobase.IFileTree.REPLACE)

        return tree

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
    GameSaveExtension = "sav"
    
    @staticmethod
    def getCloudSaveDirectory():
        steamPath = Path(find_steam_path())
        userData = steamPath.joinpath("userdata")
        for child in userData.iterdir():
            name = child.name
            try:
                userID = int(name)
            except ValueError:
                userID = -1
            if userID == -1:
                continue
            cloudSaves = child.joinpath("367500", "remote")
            if cloudSaves.exists() and cloudSaves.is_dir():
                return str(cloudSaves)
        return None
    
    def savesDirectory(self) -> QDir:
        documentsSaves = QDir(str(os.getenv('LOCALAPPDATA')) + "\\GOG.com\\Galaxy\\Applications\\49987265717041704\\Storage\\Shared\\Files")
        if self.is_steam():
            cloudSaves = self.getCloudSaveDirectory()
            if cloudSaves is None:
                return documentsSaves
            return QDir(cloudSaves)
        
        return documentsSaves