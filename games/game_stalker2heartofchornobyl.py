from typing import List
from enum import IntEnum, auto
from pathlib import Path
from PyQt6.QtCore import QDir, QFileInfo
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget
import mobase
import os
from ..basic_game import BasicGame
from ..basic_features import BasicModDataChecker, GlobPatterns, BasicLocalSavegames


class Problems(IntEnum):
    """
    Enums for IPluginDiagnose.
    """
    # PAK files placed in incorrect locations
    MISPLACED_PAK_FILES = auto()
    # Missing mod directory structure
    MISSING_MOD_DIRECTORIES = auto()


class S2HoCGame(BasicGame, mobase.IPluginFileMapper, mobase.IPluginDiagnose):
    Name = "Stalker 2: Heart of Chornobyl Plugin"
    Author = "MkHaters"
    Version = "1.1.0"

    # Game details for MO2, using paths common for Unreal Engine-based games.
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
    GameDataPath = "%GAME_PATH%/Stalker2"
    GameIniFiles = [
        "%GAME_DOCUMENTS%/Saved/Config/Windows/Game.ini",
        "%GAME_DOCUMENTS%/Saved/Config/Windows/GameUserSettings.ini",
        "%GAME_DOCUMENTS%/Saved/Config/Windows/Engine.ini"
    ]

    _main_window: QMainWindow
    _paks_tab: QWidget  # Will be S2HoCPaksTabWidget when imported

    def __init__(self):
        # Initialize parent classes.
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)
        mobase.IPluginDiagnose.__init__(self)

    def resolve_path(self, path: str) -> str:
        # Replace MO2 variables with actual paths
        path = path.replace("%USERPROFILE%", os.environ.get("USERPROFILE", ""))
        path = path.replace("%GAME_DOCUMENTS%", self.GameDocumentsDirectory)
        path = path.replace("%GAME_PATH%", self.GameDataPath)
        return path

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(S2HoCModDataChecker())
        self._register_feature(
            BasicLocalSavegames(QDir(self.resolve_path(self.GameSavesDirectory)))
        )
        
        # Create the directory more reliably
        if (
            self._organizer.managedGame()
            and self._organizer.managedGame().gameName() == self.gameName()
        ):
            # Get the absolute path as a string
            mod_path = self.paksModsDirectory().absolutePath()
            try:
                # Create the directory with parents if needed
                os.makedirs(mod_path, exist_ok=True)
                # Verify the directory was actually created
                if not os.path.exists(mod_path):
                    print(f"Warning: Failed to create directory: {mod_path}")
            except Exception as e:
                print(f"Error creating mod directory: {e}")
        
        # Initialize PAK tab when UI is ready
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
                print("No main tab widget found!")
                return

            # Import here to avoid circular imports
            from .stalker2heartofchornobyl.paks import S2HoCPaksTabWidget
            self._paks_tab = S2HoCPaksTabWidget(main_window, self._organizer)

            # Insert after the last tab (like Oblivion Remastered)
            tab_widget.addTab(self._paks_tab, "PAK Files")
            print("PAK Files tab added!")
        except Exception as e:
            print(f"Error initializing PAK tab: {e}")
            import traceback
            traceback.print_exc()

    def mappings(self) -> List[mobase.Mapping]:
        return [
            mobase.Mapping("*.pak", "Content/Paks/~mods/", False),
            mobase.Mapping("*.utoc", "Content/Paks/~mods/", False),
            mobase.Mapping("*.ucas", "Content/Paks/~mods/", False),
            mobase.Mapping("Paks/*.pak", "Content/Paks/~mods/", False),
            mobase.Mapping("Paks/*.utoc", "Content/Paks/~mods/", False),
            mobase.Mapping("Paks/*.ucas", "Content/Paks/~mods/", False),
            mobase.Mapping("~mods/*.pak", "Content/Paks/~mods/", False),
            mobase.Mapping("~mods/*.utoc", "Content/Paks/~mods/", False),
            mobase.Mapping("~mods/*.ucas", "Content/Paks/~mods/", False),
            mobase.Mapping("Content/Paks/~mods/*.pak", "Content/Paks/~mods/", False),
            mobase.Mapping("Content/Paks/~mods/*.utoc", "Content/Paks/~mods/", False),
            mobase.Mapping("Content/Paks/~mods/*.ucas", "Content/Paks/~mods/", False),
        ]

    def gameDirectory(self) -> QDir:
        return QDir(self._gamePath)
    
    def paksDirectory(self) -> QDir:
        return QDir(self.gameDirectory().absolutePath() + "/Stalker2/Content/Paks")
    
    def paksModsDirectory(self) -> QDir:
        # Use os.path.join for more reliable path construction
        path = os.path.join(self.paksDirectory().absolutePath(), "~mods")
        return QDir(path)
    
    def logicModsDirectory(self) -> QDir:
        # Update path to place LogicMods under Paks
        return QDir(self.gameDirectory().absolutePath() + "/Stalker2/Content/Paks/LogicMods")
    
    def binariesDirectory(self) -> QDir:
        return QDir(self.gameDirectory().absolutePath() + "/Stalker2/Binaries/Win64")
    
    def getModMappings(self) -> dict[str, list[str]]:
        return {
            "Content/Paks/~mods": [self.paksModsDirectory().absolutePath()],
        }
    
    def activeProblems(self) -> list[int]:
        problems = set()
        if self._organizer.managedGame() == self:
            
            # More reliable directory check using os.path
            mod_path = self.paksModsDirectory().absolutePath()
            if not os.path.isdir(mod_path):
                problems.add(Problems.MISSING_MOD_DIRECTORIES)
                print(f"Missing mod directory: {mod_path}")
            
            # Check for misplaced PAK files
            for mod in self._organizer.modList().allMods():
                mod_info = self._organizer.modList().getMod(mod)
                filetree = mod_info.fileTree()
                
                # Check for PAK files at the root level (remove LogicMods paths)
                for entry in filetree:
                    if entry.name().endswith(('.pak', '.utoc', '.ucas')) and not any(
                        entry.path().startswith(p) for p in ['Content/Paks/~mods', 'Paks', '~mods']
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
                # Create only the ~mods directory
                os.makedirs(self.paksModsDirectory().absolutePath(), exist_ok=True)
            case _:
                pass


class S2HoCModDataChecker(BasicModDataChecker):
    def __init__(self, patterns: GlobPatterns = GlobPatterns()):
        # Define valid mod directories and the file movement rules.
        move_patterns = {
            "*.pak": "Content/Paks/~mods/",
            "*.utoc": "Content/Paks/~mods/",
            "*.ucas": "Content/Paks/~mods/"
        }
        # Define valid mod roots - remove LogicMods
        valid_roots = ["Content", "Paks", "~mods"]
        base_patterns = GlobPatterns(valid=valid_roots, move=move_patterns)
        merged_patterns = base_patterns.merge(patterns)
        super().__init__(merged_patterns)


def createPlugin():
    return S2HoCGame()