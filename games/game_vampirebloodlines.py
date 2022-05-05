# -*- encoding: utf-8 -*-
import os
from pathlib import Path
from typing import List

from PyQt6.QtCore import QDir

import mobase

from ..basic_game import BasicGame, BasicGameSaveGame


class VampireModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()
        self.validDirNames = [
            "cfg",
            "cl_dlls",
            "dlg",
            "dlls",
            "maps",
            "materials",
            "media",
            "models",
            "particles",
            "python",
            "resource",
            "scripts",
            "sound",
            "vdata",
        ]

    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        for entry in tree:
            if not entry.isDir():
                continue
            if entry.name().casefold() in self.validDirNames:
                return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.INVALID


class VampireSaveGame(BasicGameSaveGame):
    _filepath: Path

    def __init__(self, filepath: Path):
        super().__init__(filepath)
        self._filepath = filepath
        self.name = None
        self.elapsedTime = None


class VampireLocalSavegames(mobase.LocalSavegames):
    def __init__(self, myGameSaveDir):
        super().__init__()
        self._savesDir = myGameSaveDir.absolutePath()

    def mappings(self, profile_save_dir):
        m = mobase.Mapping()
        m.createTarget = True
        m.isDirectory = True
        m.source = profile_save_dir.absolutePath()
        m.destination = self._savesDir

        return [m]

    def prepareProfile(self, profile):
        return profile.localSavesEnabled()


class VampireTheMasqueradeBloodlinesGame(BasicGame):
    Name = "Vampire - The Masquerade: Bloodlines Support Plugin"
    Author = "John"
    Version = "1.0.0"
    Description = "Adds support for Vampires: The Masquerade - Bloodlines"

    GameName = "Vampire - The Masquerade: Bloodlines"
    GameShortName = "vampirebloodlines"
    GameNexusName = "vampirebloodlines"
    GameNexusId = 437
    GameSteamId = [2600]
    GameGogId = [1207659240]
    GameBinary = "vampire.exe"
    GameDataPath = "vampire"
    GameDocumentsDirectory = "%GAME_PATH%/vampire/cfg"
    GameSavesDirectory = "%GAME_PATH%/vampire/SAVE"
    GameSaveExtension = "sav"
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Vampire:-The-Masquerade-%E2%80%90-Bloodlines"
    )

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = VampireModDataChecker()
        self._featureMap[mobase.SaveGameInfo] = VampireSaveGame(
            Path(self.savesDirectory().absolutePath())
        )
        self._featureMap[mobase.LocalSavegames] = VampireLocalSavegames(
            self.savesDirectory()
        )
        return True

    def initializeProfile(self, path: QDir, settings: mobase.ProfileSetting):
        # Create .cfg files if they don't exist
        for iniFile in self.iniFiles():
            iniPath = self.documentsDirectory().absoluteFilePath(iniFile)
            if not os.path.exists(iniPath):
                with open(iniPath, "w") as _:
                    pass

        super().initializeProfile(path, settings)

    def version(self):
        # Don't forget to import mobase!
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.final)

    def iniFiles(self):
        return ["autoexec.cfg", "user.cfg"]

    def listSaves(self, folder: QDir) -> List[mobase.ISaveGame]:
        ext = self._mappings.savegameExtension.get()
        return [
            VampireSaveGame(path)
            for path in Path(folder.absolutePath()).glob(f"*.{ext}")
        ]
