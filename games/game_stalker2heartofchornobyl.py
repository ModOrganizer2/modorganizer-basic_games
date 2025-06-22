import os
from enum import IntEnum, auto
from typing import List

from PyQt6.QtCore import QDir
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget

import mobase

from ..basic_features import BasicLocalSavegames, BasicModDataChecker, GlobPatterns
from ..basic_game import BasicGame


class Problems(IntEnum):
    """
    Enums for IPluginDiagnose.
    """

    MISPLACED_PAK_FILES = auto()
    MISSING_MOD_DIRECTORIES = auto()


class S2HoCGame(BasicGame, mobase.IPluginFileMapper, mobase.IPluginDiagnose):
    Name = "Stalker 2: Heart of Chornobyl Plugin"
    Author = "MkHaters"
    Version = "1.1.0"

    GameName = "Stalker 2: Heart of Chornobyl"
    GameShortName = "stalker2heartofchornobyl"
    GameNexusName = "stalker2heartofchornobyl"
    GameDocumentsDirectory = "%USERPROFILE%/AppData/Local/Stalker2"
    GameSavesDirectory = "%GAME_DOCUMENTS%/Saved/Steam/SaveGames/Data"
    GameSaveExtension = "sav"
    GameNexusId = 6944
    GameSteamId = 1643320
    GameGogId = 1529799785
    GameBinary = "Stalker2.exe"
    GameDataPath = "Stalker2"
    GameIniFiles = [
        "%GAME_DOCUMENTS%/Saved/Config/Windows/Game.ini",
        "%GAME_DOCUMENTS%/Saved/Config/Windows/GameUserSettings.ini",
        "%GAME_DOCUMENTS%/Saved/Config/Windows/Engine.ini",
    ]

    _main_window: QMainWindow
    _paks_tab: QWidget

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)
        mobase.IPluginDiagnose.__init__(self)

    def resolve_path(self, path: str) -> str:
        path = path.replace("%USERPROFILE%", os.environ.get("USERPROFILE", ""))


        if "%GAME_DOCUMENTS%" in path:
            game_docs = self.GameDocumentsDirectory.replace(
                "%USERPROFILE%", os.environ.get("USERPROFILE", "")
            )
            path = path.replace("%GAME_DOCUMENTS%", game_docs)


        if "%GAME_PATH%" in path:
            game_path = self._gamePath if hasattr(self, "_gamePath") else ""
            path = path.replace("%GAME_PATH%", game_path)


        return path

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(S2HoCModDataChecker())
        self._register_feature(
            BasicLocalSavegames(QDir(self.resolve_path(self.GameSavesDirectory)))
        )

        if (
            self._organizer.managedGame()
            and self._organizer.managedGame().gameName() == self.gameName()
        ):
            mod_path = self.paksModsDirectory().absolutePath()
            try:
                os.makedirs(mod_path, exist_ok=True)
                if not os.path.exists(mod_path):
                    self._organizer.log(
                        mobase.LogLevel.WARNING,
                        f"Failed to create directory: {mod_path}",
                    )
            except OSError as e:
                self._organizer.log(
                    mobase.LogLevel.ERROR, f"OS error creating mod directory: {e}"
                )
            except Exception as e:
                self._organizer.log(
                    mobase.LogLevel.ERROR,
                    f"Unexpected error creating mod directory: {e}",
                )

        organizer.onUserInterfaceInitialized(self.init_tab)
        return True

    def init_tab(self, main_window: QMainWindow):
        """
        Initializes the PAK management tab for Stalker 2.
        """
        try:
            if self._organizer.managedGame() != self:
                return

            self._main_window = main_window
            tab_widget: QTabWidget = main_window.findChild(QTabWidget, "tabWidget")
            if not tab_widget:
                self._organizer.log(
                    mobase.LogLevel.WARNING, "No main tab widget found!"
                )
                return

            from .stalker2heartofchornobyl.paks import S2HoCPaksTabWidget

            self._paks_tab = S2HoCPaksTabWidget(main_window, self._organizer)

            tab_widget.addTab(self._paks_tab, "PAK Files")
            self._organizer.log(mobase.LogLevel.INFO, "PAK Files tab added!")
        except ImportError as e:
            self._organizer.log(
                mobase.LogLevel.ERROR, f"Failed to import PAK tab widget: {e}"
            )
        except Exception as e:
            self._organizer.log(
                mobase.LogLevel.ERROR, f"Error initializing PAK tab: {e}"
            )
            import traceback

            traceback.print_exc()

    def mappings(self) -> List[mobase.Mapping]:
        pak_extensions = ["*.pak", "*.utoc", "*.ucas"]
        target_dir = "Content/Paks/~mods/"


        mappings = []


        for ext in pak_extensions:
            mappings.append(mobase.Mapping(ext, target_dir, False))


        source_dirs = ["Paks/", "~mods/", "Content/Paks/~mods/"]
        for source_dir in source_dirs:
            for ext in pak_extensions:
                mappings.append(mobase.Mapping(f"{source_dir}{ext}", target_dir, False))


        return mappings

    def gameDirectory(self) -> QDir:
        return QDir(self._gamePath)

    def paksDirectory(self) -> QDir:
        path = os.path.join(
            self.gameDirectory().absolutePath(), self.GameDataPath, "Content", "Paks"
        )
        return QDir(path)


    def paksModsDirectory(self) -> QDir:
        try:
            path = os.path.join(self.paksDirectory().absolutePath(), "~mods")
            return QDir(path)
        except Exception:
            fallback = os.path.join(
                self.gameDirectory().absolutePath(),
                self.GameDataPath,
                "Content",
                "Paks",
                "~mods",
            )
            return QDir(fallback)


    def logicModsDirectory(self) -> QDir:
        path = os.path.join(
            self.gameDirectory().absolutePath(),
            self.GameDataPath,
            "Content",
            "Paks",
            "LogicMods",
        )
        return QDir(path)


    def binariesDirectory(self) -> QDir:
        path = os.path.join(
            self.gameDirectory().absolutePath(),
            self.GameDataPath,
            "Binaries",
            "Win64",
        )
        return QDir(path)

    def getModMappings(self) -> dict[str, list[str]]:
        return {
            "Content/Paks/~mods": [self.paksModsDirectory().absolutePath()],
        }

    def activeProblems(self) -> list[int]:
        problems = set()
        if self._organizer.managedGame() == self:
            mod_path = self.paksModsDirectory().absolutePath()
            if not os.path.isdir(mod_path):
                problems.add(Problems.MISSING_MOD_DIRECTORIES)
                self._organizer.log(
                    mobase.LogLevel.DEBUG, f"Missing mod directory: {mod_path}"
                )

            for mod in self._organizer.modList().allMods():
                mod_info = self._organizer.modList().getMod(mod)
                filetree = mod_info.fileTree()

                for entry in filetree:
                    if entry.name().endswith((".pak", ".utoc", ".ucas")) and not any(
                        entry.path().startswith(p)
                        for p in ["Content/Paks/~mods", "Paks", "~mods"]
                    ):
                        problems.add(Problems.MISPLACED_PAK_FILES)
                        break

        return list(problems)

    def fullDescription(self, key: int) -> str:
        match key:
            case Problems.MISPLACED_PAK_FILES:
                return (
                    "Some mod packages contain PAK files that are not placed in the correct directory structure.\n\n"
                    "PAK files should be placed in one of the following locations within the mod:\n"
                    "- Content/Paks/~mods/\n"
                    "- Paks/\n"
                    "- ~mods/\n\n"
                    "Please restructure your mods to follow this directory layout."
                )
            case Problems.MISSING_MOD_DIRECTORIES:
                return (
                    "Required mod directory is missing in the game folder.\n\n"
                    "The following directory should exist:\n"
                    "- Stalker2/Content/Paks/~mods\n\n"
                    "This will be created automatically when you restart Mod Organizer 2."
                )
            case _:
                return ""

    def hasGuidedFix(self, key: int) -> bool:
        match key:
            case Problems.MISSING_MOD_DIRECTORIES:
                return True
            case _:
                return False

    def shortDescription(self, key: int) -> str:
        match key:
            case Problems.MISPLACED_PAK_FILES:
                return "Some mods have PAK files in incorrect locations."
            case Problems.MISSING_MOD_DIRECTORIES:
                return "Required mod directories are missing."
            case _:
                return ""

    def startGuidedFix(self, key: int) -> None:
        match key:
            case Problems.MISSING_MOD_DIRECTORIES:
                try:
                    os.makedirs(self.paksModsDirectory().absolutePath(), exist_ok=True)
                    self._organizer.log(
                        mobase.LogLevel.INFO, "Created missing mod directories"
                    )
                except Exception as e:
                    self._organizer.log(
                        mobase.LogLevel.ERROR, f"Failed to create mod directories: {e}"
                    )
            case _:
                pass


class S2HoCModDataChecker(BasicModDataChecker):
    def __init__(self, patterns: GlobPatterns = GlobPatterns()):
        move_patterns = {
            "*.pak": "Content/Paks/~mods/",
            "*.utoc": "Content/Paks/~mods/",
            "*.ucas": "Content/Paks/~mods/",
        }
        valid_roots = ["Content", "Paks", "~mods"]
        base_patterns = GlobPatterns(valid=valid_roots, move=move_patterns)
        merged_patterns = base_patterns.merge(patterns)
        super().__init__(merged_patterns)


def createPlugin():
    return S2HoCGame()
