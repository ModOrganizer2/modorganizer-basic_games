# -*- encoding: utf-8 -*-
import json
import os
from pathlib import Path
from typing import List, Dict

from PyQt5.QtCore import QDir, QFileInfo, QStandardPaths

import mobase

from ..basic_game import BasicGame, BasicGameSaveGame

class BlackAndWhite2SaveGame(BasicGameSaveGame):
    def __init__(self, filepath):
        super().__init__(filepath)
        self.name: str = ""

    def getName(self) -> str:
        with open(self._filepath.joinpath('SaveGame.inf'), 'rb') as info:
            info.read(4)
            name = u''
            while True:
                char = info.read(2)
                name = name + char.decode('utf-16')
                if char[0] == 0:
                    break
            info.close()
            return name
        return super.getName()
        
    def getSaveGroupIdentifier(self):
        return path.parent.parent.name
  
    
    
    
class BlackAndWhite2Game(BasicGame):

    Name = "Black & White 2 Support Plugin"
    Author = "Ilyu"
    Version = "0.3.0"

    GameName = "Black & White 2"
    GameShortName = "BW2"
    GameNexusName = "blackandwhite2"
    GameBinary = "white.exe"
    GameDataPath = r""
    GameDocumentsDirectory = "%DOCUMENTS%/Black & White 2"
    GameSavesDirectory = "%GAME_DOCUMENTS%/Profiles"
    
    def executables(self) -> List[mobase.ExecutableInfo]:
        execs = super().executables()
        
        '''
        A bat file to load modded executables from VFS.
        '''
        workaroundPath = self._gamePath + '/white.bat'
        
        try:
            workaround = open(workaroundPath, 'rt')
        except FileNotFoundError:
            with open(workaroundPath, 'wt') as workaround:
                workaround.write('start "" "white.exe"')
        workaround.close()
        
                
        execs.append(
            mobase.ExecutableInfo(
                self.GameShortName + ' Modded Exec',
                QFileInfo(workaroundPath)
            )
        )
        
        return execs
    
    def listSaves(self, folder: QDir) -> List[mobase.ISaveGame]:
        profiles = list()
        for path in Path(folder.absolutePath()).glob("*/Saved Games/*"):
            if path.name == 'Autosave' or path.name == 'Pictures':
                continue
            profiles.append(path)
            
            
        return [BlackAndWhite2SaveGame(path) for path in profiles]
        
class BOTGGame(BlackAndWhite2Game):

    Name = "Black & White 2 Battle of the Gods Support Plugin"
    Author = "Ilyu"

    GameName = "Black & White 2 Battle of the Gods"
    GameShortName = "BOTG"
    GameBinary = "white.exe"
    GameDataPath = r""
    GameDocumentsDirectory = "%DOCUMENTS%/Black & White 2 - Battle of the Gods"
    GameSavesDirectory = "%GAME_DOCUMENTS%/Profiles"
   