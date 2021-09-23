# -*- encoding: utf-8 -*-

from pathlib import Path
from typing import List, Optional
from enum import IntEnum

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

    def hasValidFolders(self, tree: mobase.IFileTree) -> bool:
        for e in tree:
            if e.isDir():
                if e.name().lower() in self._valid_folders:
                    return True

        return False

    def findLostDir(self, tree: mobase.IFileTree) -> mobase.IFileTree:
        if len(tree) == 1:
            sub: mobase.IFileTree = tree[0]
            if isinstance(sub, mobase.IFileTree) and self.hasValidFolders(sub):
                return sub

    def findLostData(self, tree: mobase.IFileTree) -> List[mobase.IFileTree]:
        lost_db: List[mobase.IFileTree] = []

        for e in tree:
            if e.isFile():
                if e.suffix().lower().startswith("db"):
                    lost_db.append(e)

        return lost_db

    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        if self.hasValidFolders(tree):
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


class Content(IntEnum):
    INTERFACE = 0
    TEXTURE = 1
    MESH = 2
    SCRIPT = 3
    SOUND = 4
    MCM = 5
    CONFIG = 6


class StalkerAnomalyModDataContent(mobase.ModDataContent):
    def __init__(self):
        super().__init__()

    def getAllContents(self) -> List[mobase.ModDataContent.Content]:
        return [
            mobase.ModDataContent.Content(
                Content.INTERFACE, "Interface", ":/MO/gui/content/interface"
            ),
            mobase.ModDataContent.Content(
                Content.TEXTURE, "Textures", ":/MO/gui/content/texture"
            ),
            mobase.ModDataContent.Content(
                Content.MESH, "Meshes", ":/MO/gui/content/mesh"
            ),
            mobase.ModDataContent.Content(
                Content.SCRIPT, "Scripts", ":/MO/gui/content/script"
            ),
            mobase.ModDataContent.Content(
                Content.SOUND, "Sounds", ":/MO/gui/content/sound"
            ),
            mobase.ModDataContent.Content(Content.MCM, "MCM", ":/MO/gui/content/menu"),
            mobase.ModDataContent.Content(
                Content.CONFIG, "Configs", ":/MO/gui/content/inifile"
            ),
        ]

    def findFileExt(
        self,
        tree: mobase.IFileTree,
        ext: List[str],
        ignore: Optional[List[str]] = [],
    ) -> bool:
        for e in tree:
            if e.isDir():
                if e.name().lower() in ignore:
                    continue
                if self.findFileExt(e, ext):
                    return True
            elif e.isFile():
                if e.suffix().lower() in ext:
                    return True

        return False

    def findFilePart(self, entry: mobase.IFileTree, string: str) -> bool:
        for e in entry:
            if e.isDir():
                if self.findFilePart(e, string):
                    return True
            elif e.isFile():
                if string in e.name().lower():
                    return True

        return False

    def getContentsFor(self, tree: mobase.IFileTree) -> List[int]:
        content: List[int] = []
        gamedata: mobase.IFileTree = tree.find("gamedata")
        if not gamedata:
            return []

        textures: mobase.IFileTree = gamedata.find("textures")
        if textures:
            if self.findFileExt(textures, ["dds", "thm"], ["ui"]):
                content.append(Content.TEXTURE)
            ui: mobase.IFileTree = textures.find("ui")
            if ui:
                if self.findFileExt(ui, ["dds", "thm"]):
                    content.append(Content.INTERFACE)

        meshes: mobase.IFileTree = gamedata.find("meshes")
        if meshes:
            if self.findFileExt(meshes, ["omf", "ogf"]):
                content.append(Content.MESH)

        scripts: mobase.IFileTree = gamedata.find("scripts")
        if scripts:
            if self.findFileExt(scripts, ["script"]):
                content.append(Content.SCRIPT)
            if self.findFilePart(scripts, "_mcm"):
                content.append(Content.MCM)

        sounds: mobase.IFileTree = gamedata.find("sounds")
        if sounds:
            if self.findFileExt(sounds, ["ogg"]):
                content.append(Content.SOUND)

        configs: mobase.IFileTree = gamedata.find("configs")
        if configs:
            if self.findFileExt(configs, ["ltx"], ["ui"]):
                content.append(Content.CONFIG)
            config_ui: mobase.IFileTree = configs.find("ui")
            if config_ui:
                if self.findFileExt(config_ui, ["xml"]):
                    content.append(Content.INTERFACE)

        return content


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
    Version = "0.4.0"
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
        self._featureMap[mobase.ModDataContent] = StalkerAnomalyModDataContent()
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
