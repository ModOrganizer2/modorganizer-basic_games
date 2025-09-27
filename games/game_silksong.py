from __future__ import annotations
import fnmatch
from pathlib import Path
from PyQt6.QtCore import QDir
import mobase

from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_features.basic_save_game_info import BasicGameSaveGame
from ..basic_features.utils import is_directory
from ..basic_game import BasicGame


class SilksongModDataChecker(BasicModDataChecker):
    def __init__(self, patterns: GlobPatterns | None = None):
        super().__init__(
            GlobPatterns(
                valid=[
                    "BepInEx",
                    "doorstop_config.ini", 
                    "winhttp.dll",
                    ".doorstop_version",
                ],
                delete=[
                    "*.txt",
                    "*.md",
                    "manifest.json", 
                    "icon.png",
                ],
            ).merge(patterns or GlobPatterns()),
        )

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        if self._has_bepinex_structure(filetree):
            return self.VALID
            
        return self.FIXABLE

    def _has_bepinex_structure(self, filetree: mobase.IFileTree) -> bool:
        """Check if the mod has BepInEx folder structure"""
        for entry in filetree:
            name = entry.name().lower()
            if name in ["bepinex", "doorstop_config.ini", "winhttp.dll", ".doorstop_version"]:
                return True
            if entry.isDir():
                if self._has_bepinex_structure(entry):
                    return True
        return False

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        filetree = super().fix(filetree)
        if not self._has_bepinex_structure(filetree):
            items_to_move = list(filetree)
            for item in items_to_move:
                filetree.move(item, f"BepInEx/plugins/{item.name()}")
            
        return filetree


class SilksongGame(BasicGame):
    Name = "Hollow Knight: Silksong Support Plugin"
    Author = "Assistant"
    Version = "1.0.0"

    GameName = "Hollow Knight: Silksong" 
    GameShortName = "hollowknightsilksong"
    GameNexusName = "hollowknightsilksong"
    GameSteamId = 1030300
    GameBinary = r"Hollow Knight Silksong.exe"
    GameDataPath = ""
    GameSavesDirectory = r"%USERPROFILE%\AppData\LocalLow\Team Cherry\Hollow Knight Silksong"
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Hollow-Knight-Silksong"
    )

    _forced_libraries = ["winhttp.dll"]

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(SilksongModDataChecker())
        return True

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        saves = []
        save_dir = Path(folder.absolutePath())
        
        if save_dir.exists():
            for pattern in ["*.save", "user*.dat"]:
                saves.extend(BasicGameSaveGame(f) for f in save_dir.rglob(pattern))
                
        return saves

    def executables(self) -> list[mobase.ExecutableInfo]:
        return [
            mobase.ExecutableInfo(
                self.gameName(),
                self.gameDirectory().absoluteFilePath(self.binaryName()),
            )
        ]

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        return [
            mobase.ExecutableForcedLoadSetting(self.binaryName(), lib).withEnabled(True)
            for lib in self._forced_libraries
        ]