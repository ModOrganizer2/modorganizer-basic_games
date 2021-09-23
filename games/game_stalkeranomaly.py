# -*- encoding: utf-8 -*-

from pathlib import Path
from typing import List

from PyQt5.QtCore import QDir, QFileInfo

import mobase

from ..basic_features.basic_save_game_info import BasicGameSaveGame
from ..basic_game import BasicGame


class StalkerAnomalyModDataChecker(mobase.ModDataChecker):
    _valid_folders: List[str] = [
        "appdata",
        "bin",
        "db",
        "gamedata",
    ]

    def __init__(self):
        super().__init__()

    def findLostDir(
        self, tree: mobase.IFileTree
    ) -> mobase.FileTreeEntry:
        if len(tree) == 1:
            sub: mobase.FileTreeEntry = tree[0]
            if sub.isDir():
                return sub

    def findLostData(
        self, tree: mobase.IFileTree
    ) -> List[mobase.FileTreeEntry]:
        lost_db: List[mobase.FileTreeEntry] = []

        for e in tree:
            if e.isFile():
                if e.suffix().lower().startswith("db"):
                    lost_db.append(e)

        return lost_db


    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        for e in tree:
            if e.isDir():
                if e.name().lower() in self._valid_folders:
                    return mobase.ModDataChecker.VALID

        if self.findLostDir(tree):
            return mobase.ModDataChecker.FIXABLE

        if self.findLostData(tree):
            return mobase.ModDataChecker.FIXABLE

        return mobase.ModDataChecker.INVALID

    def fix(self, tree: mobase.IFileTree) -> mobase.IFileTree:
        lost_dir = self.findLostDir(tree)
        if lost_dir:
            tree.merge(lost_dir)
            lost_dir.detach()

        lost_db = self.findLostData(tree)
        if lost_db:
            rfolder = tree.addDirectory("db").addDirectory("mods")
            for r in lost_db:
                rfolder.insert(r, mobase.IFileTree.REPLACE)

        return tree



class StalkerAnomalySaveGame(BasicGameSaveGame):
    def allFiles(self) -> List[str]:
        filepath = self.getFilepath()
        return [
            filepath,
            filepath.replace("scop", "scoc"),
            filepath.replace("scop", "dds"),
        ]


class StalkerAnomalyGame(BasicGame, mobase.IPluginFileMapper):
    Name = "STALKER Anomaly"
    Author = "Qudix"
    Version = "0.3.1"
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
                QFileInfo(self.gameDirectory(), "AnomalyLauncher.exe"),
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX11-AVX)",
                QFileInfo(self.gameDirectory(), "bin/AnomalyDX11AVX.exe"),
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX11)", QFileInfo(self.gameDirectory(), "bin/AnomalyDX11.exe")
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX10-AVX)",
                QFileInfo(self.gameDirectory(), "bin/AnomalyDX10AVX.exe"),
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX10)", QFileInfo(self.gameDirectory(), "bin/AnomalyDX10.exe")
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX9-AVX)",
                QFileInfo(self.gameDirectory(), "bin/AnomalyDX9AVX.exe"),
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX9)", QFileInfo(self.gameDirectory(), "bin/AnomalyDX9.exe")
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX8-AVX)",
                QFileInfo(self.gameDirectory(), "bin/AnomalyDX8AVX.exe"),
            ),
            mobase.ExecutableInfo(
                "Anomaly (DX8)", QFileInfo(self.gameDirectory(), "bin/AnomalyDX8.exe")
            ),
        ]

    def listSaves(self, folder: QDir) -> List[mobase.ISaveGame]:
        ext = self._mappings.savegameExtension.get()
        return [
            StalkerAnomalySaveGame(path)
            for path in Path(folder.absolutePath()).glob(f"*.{ext}")
        ]

    def mappings(self) -> List[mobase.Mapping]:
        self.gameDirectory().mkdir("appdata")

        m = mobase.Mapping()
        m.createTarget = True
        m.isDirectory = True
        m.source = self.gameDirectory().filePath("appdata")
        m.destination = self.gameDirectory().filePath("appdata")
        return [m]
