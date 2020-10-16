# -*- encoding: utf-8 -*-

from typing import List

from PyQt5.QtCore import QFileInfo

import mobase

from ..basic_game import BasicGame

class StalkerAnomalyModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()
    
    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        if tree.exists("db") or tree.exists("appdata") or tree.exists("gamedata"):
            return mobase.ModDataChecker.VALID
        else:
            return mobase.ModDataChecker.INVALID

class StalkerAnomalyGame(BasicGame, mobase.IPluginFileMapper):
    Name = "STALKER Anomaly"
    Author = "Qudix"
    Version = "0.3.0"
    Description = "Adds support for STALKER Anomaly"

    GameName = "STALKER Anomaly"
    GameShortName = "stalkeranomaly"
    GameBinary = "AnomalyLauncher.exe"
    GameDataPath = ""
    
    GameSaveExtension = "scop"
    GameSavesDirectory = "%GAME_PATH%/appdata/savedgames"

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)
    
    def init(self, organizer: mobase.IOrganizer):
        BasicGame.init(self, organizer)
        self._featureMap[mobase.ModDataChecker] = StalkerAnomalyModDataChecker()
        return True

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Anomaly Launcher", 
                QFileInfo(self.gameDirectory(), "AnomalyLauncher.exe")
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX11-AVX)", 
                QFileInfo(self.gameDirectory(), "bin/AnomalyDX11AVX.exe")
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX11)", 
                QFileInfo(self.gameDirectory(), "bin/AnomalyDX11.exe")
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX10-AVX)", 
                QFileInfo(self.gameDirectory(), "bin/AnomalyDX10AVX.exe")
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX10)", 
                QFileInfo(self.gameDirectory(), "bin/AnomalyDX10.exe")
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX9-AVX)", 
                QFileInfo(self.gameDirectory(), "bin/AnomalyDX9AVX.exe")
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX9)", 
                QFileInfo(self.gameDirectory(), "bin/AnomalyDX9.exe")
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX8-AVX)", 
                QFileInfo(self.gameDirectory(), "bin/AnomalyDX8AVX.exe")
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX8)", 
                QFileInfo(self.gameDirectory(), "bin/AnomalyDX8.exe")
            )
        ]

    def mappings(self) -> List[mobase.Mapping]:
        self.gameDirectory().mkdir("appdata")
        
        m = mobase.Mapping()
        m.createTarget = True
        m.isDirectory = True
        m.source = self.gameDirectory().filePath("appdata")
        m.destination = self.gameDirectory().filePath("appdata")
        return [m]