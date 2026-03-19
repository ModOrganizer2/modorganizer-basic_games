from functools import cached_property
from pathlib import Path
import os
import shutil

import mobase
from PyQt6.QtCore import QDir, QFileInfo

from ..basic_game import BasicGame


class NoitaModDataChecker(mobase.ModDataChecker):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self.organizer: mobase.IOrganizer = organizer
        self.organizer.modList().onModInstalled(self._Fix_Installed_Mod)
        self.needsNameFix = False

    def move_overwrite_merge(self, source, destination):
        if not os.path.exists(destination):
            shutil.move(source, destination)
            return
        if os.path.isfile(source):
            os.replace(source, destination)
            return
        for item in os.listdir(source):
            s_item = os.path.join(source, item)
            d_item = os.path.join(destination, item)
            self.move_overwrite_merge(s_item, d_item)
        os.rmdir(source)

    def _Fix_Installed_Mod(self, mod: mobase.IModInterface):
        if not self.needsNameFix:
            return
        GameModsPath = self.organizer.managedGame().GameModsPath
        filetree: mobase.IFileTree = mod.fileTree()
        fixed = False
        modname = mod.name()
        if filetree is not None and filetree.exists(
            GameModsPath + "/FOLDERNAME", mobase.IFileTree.DIRECTORY
        ):
            path = mod.absolutePath()
            old_path = os.path.join(path, GameModsPath + "/FOLDERNAME")
            new_path = os.path.join(path, GameModsPath + f"/{modname}")
            self.move_overwrite_merge(old_path, new_path)
            fixed = True
        if not fixed:
            return
        self.needsNameFix = False

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        if filetree.exists("mods", mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.FIXABLE

    def fileExistsInNextSubDir(self, filetree: mobase.IFileTree, name: str):
        for branch in filetree:
            if branch is not None and branch.isDir():
                for e in branch:
                    if e is not None and e.name() == name:
                        return True
        return False

    def allMoveTo(self, filetree: mobase.IFileTree, toMoveTo: str):
        entriesToMove: list[mobase.FileTreeEntry] = []
        retVal = 0
        for e in filetree:
            if e is not None:
                entriesToMove.append(e)
        for e in entriesToMove:
            filetree.move(e, toMoveTo, mobase.IFileTree.MERGE)
            retVal = 1
        return retVal

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        GameModsPath = self.organizer.managedGame().GameModsPath
        treefixed = 0
        if filetree.exists("mod.xml", mobase.IFileTree.FILE):
            treefixed = self.allMoveTo(filetree, GameModsPath + "/FOLDERNAME/")
            if treefixed == 1:
                self.needsNameFix = True
        if self.fileExistsInNextSubDir(filetree, "mod.xml"):
            filetree.move(filetree[0], GameModsPath + "/", mobase.IFileTree.MERGE)
            treefixed = 1
        if treefixed == 0:
            return None
        return filetree


class NoitaGame(BasicGame):
    Name = "Noita Support Plugin"
    Author = "modworkshop"
    Version = "1"
    GameName = "Noita"
    GameShortName = "noita"
    GameSteamId = 881100
    GameBinary = "noita.exe"
    GameDataPath = "%GAME_PATH%"
    GameModsPath = "mods"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = NoitaModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        return True

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Noita",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
            mobase.ExecutableInfo(
                "Noita Dev",
                QFileInfo(
                    self.gameDirectory(),
                    "noita_dev.exe",
                ),
            ),
        ]

    @cached_property
    def _base_dlls(self) -> set[str]:
        base_dir = Path(self.gameDirectory().absolutePath())
        return {str(f.relative_to(base_dir)) for f in base_dir.glob("*.dll")}

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        try:
            efls = super().executableForcedLoads()
        except AttributeError:
            efls = []
        libs: set[str] = set()
        tree: mobase.IFileTree | mobase.FileTreeEntry | None = (
            self._organizer.virtualFileTree()
        )
        if type(tree) is not mobase.IFileTree:
            return efls
        for e in tree:
            relpath = e.pathFrom(tree)
            if relpath and e.hasSuffix("dll") and relpath not in self._base_dlls:
                libs.add(relpath)
        exes = self.executables()
        efls = efls + [
            mobase.ExecutableForcedLoadSetting(
                exe.binary().fileName(), lib
            ).withEnabled(True)
            for lib in libs
            for exe in exes
        ]
        return efls

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        modsPath = self.dataDirectory().absolutePath()
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)
        super().initializeProfile(directory, settings)
