import os
import shutil
from functools import cached_property
from pathlib import Path

from PyQt6.QtCore import QDir, QFileInfo

import mobase

from ..basic_game import BasicGame


class EmuVRModDataChecker(mobase.ModDataChecker):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self.organizer: mobase.IOrganizer = organizer

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        GameDataUGCMods = getattr(self.organizer.managedGame(), "GameDataUGCMods", "")
        if filetree.exists(GameDataUGCMods, mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.FIXABLE

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree | None:
        GameDataUGCMods = (
            getattr(self.organizer.managedGame(), "GameDataUGCMods", "") + "/"
        )

        # If the tree has no name, MO2 is working with a normal virtual tree and
        # entries can be moved virtually. Non-zipped installer paths set a tree name,
        # so those files need to be moved on disk instead.
        if filetree.name() == "":
            for branch in list(filetree):
                if isinstance(branch, mobase.IFileTree):
                    for e in list(branch):
                        if e.isFile() and e.suffix().casefold() == "ugc":
                            filetree.move(e, GameDataUGCMods, mobase.IFileTree.MERGE)
                elif branch.isFile() and branch.suffix().casefold() == "ugc":
                    filetree.move(branch, GameDataUGCMods, mobase.IFileTree.MERGE)
        else:
            mod_name = filetree.name()
            mod_path = os.path.join(self.organizer.modsPath(), mod_name)
            target_dir = os.path.join(mod_path, GameDataUGCMods)

            for branch in list(filetree):
                if branch.isFile() and branch.suffix().casefold() == "ugc":
                    os.makedirs(target_dir, exist_ok=True)
                    src = os.path.join(mod_path, branch.name())
                    dst = os.path.join(target_dir, branch.name())
                    shutil.move(src, dst)

        return filetree


class EmuVRGame(BasicGame):
    Name = "Emu VR Support Plugin"
    Author = "ModWorkshop"
    CategorySource = "modworkshop"
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
            mobase.ExecutableInfo(
                "Force SteamVR", QFileInfo(self.gameDirectory(), "Force SteamVR.exe")
            ),
            mobase.ExecutableInfo(
                "Force Oculus", QFileInfo(self.gameDirectory(), "Force Oculus.exe")
            ),
            mobase.ExecutableInfo(
                "Force Virtual Desktop Streamer",
                QFileInfo(self.gameDirectory(), "Force Virtual Desktop Streamer.exe"),
            ),
            mobase.ExecutableInfo(
                "Force Desktop", QFileInfo(self.gameDirectory(), "Force Desktop.exe")
            ),
        ]

    def iniFiles(self):
        return ["settings.ini"]

    @cached_property
    def baseDlls(self) -> set[str]:
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
            if relpath and e.hasSuffix("dll") and relpath not in self.baseDlls:
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
        modsPath = os.path.join(
            self.dataDirectory().absolutePath(),
            self.GameDataUGCMods,
        )
        os.makedirs(modsPath, exist_ok=True)
        super().initializeProfile(directory, settings)
