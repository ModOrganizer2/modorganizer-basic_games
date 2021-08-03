# -*- encoding: utf-8 -*-
import json
import os
from pathlib import Path
from typing import List, Dict

from PyQt5.QtCore import QDir, QFileInfo, QStandardPaths

import mobase

from ..basic_game import BasicGame, BasicGameSaveGame

class BlackAndWhite2ModDataChecker(mobase.ModDataChecker):
    _validFolderTree = {
        '<black & white 2>': ['Audio', 'Data', 'PlugIns', 'Scripts'],
        'Audio': ['Dialogue','Music','SFX'],
        'Music': ['BuildingMusic', 'Chant', 'Cutscene', 'Dynamic Music', 'Epicspell', 'TownAlignment'],
        'SFX': ['Atmos', 'Creature', 'game', 'Script', 'Spells', 'Video'],
        'Data': ['Art', 'Balance', 'ctr', 'effects', 'EncryptedShaders', 'font', 'HandDemo', 'Interface',
        'landscape', 'Light Particle Effects', 'Lipsync', 'Physics', 'SFX', 'Shaders', 'Symbols', 'Text', 
        'Textures', 'Tutorial AVI', 'VisualEffects', 'WeatherSystem', 'Zones'],
        'Art': ['binary_anim_libs', 'binary_animations', 'features', 'models', 'skins', 'textures', 'water'],
        'ctr': ['badvisor_evil', 'badvisor_good', 'bape', 'bgorilla', 'bhand', 'blion', 'btiger', 'bwolf', 'damage', 'siren'],
        'font': ['Asian'],
        'Asian': ['Korean', 'Traditional Chinese'],
        'landscape': ['aztec', 'BW2', 'egyptian', 'generic', 'greek', 'japanese', 'norse', 'skysettings'],
        'SFX': ['Grass'],
        'Tutorial AVI': ['placeholder', 'stills'],
        'VisualEffects': ['textures'],
        'Scripts': ['BW2']
    }

    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        
        valid = 1
        
        for entry in tree:
            if entry.name == '<black & white 2>':
                return mobase.ModDataChecker.VALID
            if not entry.isDir():
                continue
                
            if entry.parent() is None:
                continue
            else:
                parentName = entry.parent().name()
                if entry.parent().parent() is None:
                    parentName = '<black & white 2>'
                if parentName not in self._validFolderTree.keys():
                    return mobase.ModDataChecker.INVALID
            
            
            if not entry.name() in self._validFolderTree[parentName]:
                return mobase.ModDataChecker.INVALID
        
        return mobase.ModDataChecker.VALID

class BlackAndWhite2SaveGame(BasicGameSaveGame):
    def __init__(self, filepath):
        super().__init__(filepath)
        self.name: str = ""

    def allFiles(self) -> List[str]:
        return [file for file in self.filepath.glob('*') if file.is_file()]

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
    Version = "0.5.0"

    GameName = "Black & White 2"
    GameShortName = "BW2"
    GameNexusName = "blackandwhite2"
    GameDataPath = "%GAME_PATH%"
    GameBinary = "white.exe"
    GameDocumentsDirectory = "%DOCUMENTS%/Black & White 2"
    GameSavesDirectory = "%GAME_DOCUMENTS%/Profiles"


    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = BlackAndWhite2ModDataChecker()
        return True

    def executables(self) -> List[mobase.ExecutableInfo]:
        execs = super().executables()
        
        '''
        A bat file to load modded executables from VFS.
        '''
        workaroundPath = self._gamePath + '/' + self.GameBinary[:-4] + '.bat'
        
        try:
            workaround = open(workaroundPath, 'rt')
        except FileNotFoundError:
            with open(workaroundPath, 'wt') as workaround:
                workaround.write('start "" "' + self.GameBinary + '"' )
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
    
    GameName = "Black & White 2 Battle of the Gods"
    GameShortName = "BOTG"
    GameBinary = "BattleOfTheGods.exe"
    GameDocumentsDirectory = "%DOCUMENTS%/Black & White 2 - Battle of the Gods"
    GameSavesDirectory = "%GAME_DOCUMENTS%/Profiles"
   