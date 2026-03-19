import os
import shutil
import mobase

from pathlib import Path
from functools import cached_property

from ..basic_game import BasicGame

from PyQt6.QtCore import QDir, QFileInfo


class EmuVRModDataChecker(mobase.ModDataChecker):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self.organizer: mobase.IOrganizer = organizer

    def dataLooksValid(self, filetree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        GameDataUGCMods = self.organizer.managedGame().GameDataUGCMods
        if filetree.exists(GameDataUGCMods, mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.FIXABLE

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        GameDataUGCMods = self.organizer.managedGame().GameDataUGCMods + "/"
        treefixed = 0
        for branch in filetree:
            mod_name = filetree.name()
            if mod_name == "":
                mod_name = branch.name()
            mod_path = os.path.join(self.organizer.modsPath(), mod_name)
            if filetree.createOrphanTree("OrphanTree") is None and os.path.exists(mod_path) and branch.suffix().casefold() == "ugc":
                os.makedirs(os.path.join(mod_path, GameDataUGCMods), exist_ok=True)
                shutil.move(os.path.join(mod_path, branch.name()), os.path.join(mod_path, GameDataUGCMods, branch.name()))
                treefixed = 1
            else:
                if branch is not None:
                    if branch.isDir():
                        for e in branch:
                            if e is not None and e.isFile() and e.suffix().casefold() == "ugc":
                                filetree.move(e, GameDataUGCMods, mobase.IFileTree.MERGE)
                                treefixed = 1
                    elif branch.suffix().casefold() == "ugc":
                        filetree.move(branch, GameDataUGCMods, mobase.IFileTree.MERGE)
                        treefixed = 1
        if treefixed == 0:
            return None
        return filetree


class EmuVRGame(BasicGame):
    Name = "Emu VR Support Plugin"
    Author = "modworkshop"
    Version = "1"
    GameName = "Emu VR"
    GameShortName = "emuvr"
    GameBinary = "EmuVR.exe"
    GameDataPath = "%GAME_PATH%"
    GameDataUGCMods = "Custom/UGC"
    GameDocumentsDirectory = "%GAME_PATH%/Saved Data"
    GameSavesDirectory = "%GAME_PATH%/Saved Data"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = EmuVRModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        return True

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Emu VR",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
            mobase.ExecutableInfo("Force SteamVR", QFileInfo(self.gameDirectory(), "Force SteamVR.exe")),
            mobase.ExecutableInfo("Force Oculus", QFileInfo(self.gameDirectory(), "Force Oculus.exe")),
            mobase.ExecutableInfo("Force Virtual Desktop Streamer", QFileInfo(self.gameDirectory(), "Force Virtual Desktop Streamer.exe")),
            mobase.ExecutableInfo("Force Desktop", QFileInfo(self.gameDirectory(), "Force Desktop.exe")),
        ]

    def iniFiles(self):
        return ["settings.ini"]

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
        tree: mobase.IFileTree | mobase.FileTreeEntry | None = self._organizer.virtualFileTree()
        if type(tree) is not mobase.IFileTree:
            return efls
        for e in tree:
            relpath = e.pathFrom(tree)
            if relpath and e.hasSuffix("dll") and relpath not in self._base_dlls:
                libs.add(relpath)
        exes = self.executables()
        efls = efls + [mobase.ExecutableForcedLoadSetting(exe.binary().fileName(), lib).withEnabled(True) for lib in libs for exe in exes]
        return efls

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        modsPath = self.dataDirectory().absolutePath()
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)
        super().initializeProfile(directory, settings)
