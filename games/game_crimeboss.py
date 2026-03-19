import json
import os
import shutil
import mobase

from enum import IntEnum, auto
from pathlib import Path
from functools import cached_property

from .unreal_tabs.constants import DEFAULT_UE4SS_MODS, UE4SSModInfo
from .unreal_tabs.manage_paks.widget import PaksTabWidget
from .unreal_tabs.manage_ue4ss.widget import UE4SSTabWidget

from ..basic_game import BasicGame

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget
from PyQt6.QtCore import QDir, QFileInfo


class Content(IntEnum):
    UCAS = auto()
    UTOC = auto()
    PAK = auto()
    UE4SS = auto()
    DLL = auto()
    BK2 = auto()


class CrimeBossModDataContent(mobase.ModDataContent):
    contents: list[int] = []
    GAMECONTENTS: list[tuple[Content, str, str, bool] | tuple[Content, str, str]] = [
        (Content.UCAS, "UCAS", ":/MO/gui/content/geometries"),
        (Content.UTOC, "UTOC", ":/MO/gui/content/inifile"),
        (Content.PAK, "PAK", ":/MO/gui/content/geometries"),
        (Content.UE4SS, "UE4SS", ":/MO/gui/content/script"),
        (Content.DLL, "DLL", ":/MO/gui/content/skse"),
        (Content.BK2, "Video", ":/MO/gui/content/skse"),
    ]

    def getAllContents(self) -> list[mobase.ModDataContent.Content]:
        return [mobase.ModDataContent.Content(id, name, icon, *filter_only) for id, name, icon, *filter_only in self.GAMECONTENTS]

    def walkContent(self, path: str, entry: mobase.FileTreeEntry):
        if entry.isFile():
            match entry.suffix().casefold():
                case "utoc":
                    self.contents.add(Content.UTOC)
                case "ucas":
                    self.contents.add(Content.UCAS)
                case "pak":
                    self.contents.add(Content.PAK)
                case "lua":
                    self.contents.add(Content.UE4SS)
                case "dll":
                    self.contents.add(Content.DLL)
                case "bk2":
                    self.contents.add(Content.BK2)
                case _:
                    pass
        return mobase.IFileTree.WalkReturn.CONTINUE

    def getContentsFor(self, filetree: mobase.IFileTree) -> list[int]:
        self.contents: set[int] = set()
        filetree.walk(self.walkContent, "/")
        return list(self.contents)


class CrimeBossModDataChecker(mobase.ModDataChecker):
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
        GameDataNativeMods = self.organizer.managedGame().GameDataNativeMods
        filetree: mobase.IFileTree = mod.fileTree()
        fixed = False
        modname = mod.name()
        if filetree is not None and filetree.exists(GameDataNativeMods + "/FOLDERNAME", mobase.IFileTree.DIRECTORY):
            path = mod.absolutePath()
            old_path = os.path.join(path, GameDataNativeMods + "/FOLDERNAME")
            new_path = os.path.join(path, GameDataNativeMods + f"/{modname}")
            self.move_overwrite_merge(old_path, new_path)
            fixed = True
        if not fixed:
            return
        self.needsNameFix = False

    def dataLooksValid(self, filetree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        GameDataUE4SSMods = self.organizer.managedGame().GameDataUE4SSMods
        GameDataPakMods = self.organizer.managedGame().GameDataPakMods
        GameDataNativeMods = self.organizer.managedGame().GameDataNativeMods
        if filetree.exists(GameDataPakMods, mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        if filetree.exists(os.path.dirname(GameDataUE4SSMods), mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        if filetree.exists(GameDataNativeMods, mobase.IFileTree.DIRECTORY) and not filetree.exists("UE4SS.dll", mobase.IFileTree.FILE):
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
        GameDataUE4SSMods = self.organizer.managedGame().GameDataUE4SSMods + "/"
        GameDataPakMods = self.organizer.managedGame().GameDataPakMods + "/"
        GameDataNativeMods = self.organizer.managedGame().GameDataNativeMods + "/"
        GameDataMovies = self.organizer.managedGame().GameDataMovies + "/"
        treefixed = 0
        if filetree.exists("UE4SS.dll", mobase.IFileTree.FILE):
            treefixed = self.allMoveTo(filetree, os.path.dirname(os.path.dirname(GameDataUE4SSMods)) + "/")
            if treefixed == 1:
                return filetree
        if filetree.exists("Content", mobase.IFileTree.DIRECTORY):
            treefixed = self.allMoveTo(filetree, GameDataNativeMods + "FOLDERNAME/")
            if treefixed == 1:
                self.needsNameFix = True
        if self.fileExistsInNextSubDir(filetree, "Content"):
            filetree.move(filetree[0], GameDataNativeMods + "/", mobase.IFileTree.MERGE)
            treefixed = 1
        if treefixed == 0:
            allowedUnzippedExt = ["pak", "utoc", "ucas", "bk2", "dll"]
            entriesToMove: list[mobase.FileTreeEntry] = []
            for e in filetree:
                if e is not None:
                    if e.isFile():
                        fileext = e.suffix().casefold()
                        if fileext in allowedUnzippedExt:
                            mod_name = filetree.name()
                            if mod_name == "":
                                mod_name = e.name()
                            mod_path = os.path.join(self.organizer.modsPath(), mod_name)
                            if filetree.createOrphanTree("OrphanTree") is None and os.path.exists(mod_path):
                                match e.suffix().casefold():
                                    case "pak" | "utoc" | "ucas":
                                        os.makedirs(os.path.join(mod_path, GameDataPakMods), exist_ok=True)
                                        shutil.move(os.path.join(mod_path, e.name()), os.path.join(mod_path, GameDataPakMods, e.name()))
                                    case "bk2":
                                        os.makedirs(os.path.join(mod_path, GameDataMovies), exist_ok=True)
                                        shutil.move(os.path.join(mod_path, e.name()), os.path.join(mod_path, GameDataMovies, e.name()))
                                    case _:
                                        pass
                                treefixed = 1
                            else:
                                entriesToMove.append(e)
            if entriesToMove is not None:
                for e in entriesToMove:
                    match e.suffix().casefold():
                        case "pak" | "utoc" | "ucas":
                            filetree.move(e, GameDataPakMods, mobase.IFileTree.MERGE)
                        case "dll":
                            filetree.move(e, os.path.dirname(GameDataUE4SSMods) + "/", mobase.IFileTree.MERGE)
                        case "bk2":
                            filetree.move(e, GameDataMovies, mobase.IFileTree.MERGE)
                        case _:
                            pass
                treefixed = 1
        if treefixed == 0:
            return None
        return filetree


class CrimeBossGame(BasicGame):
    Name = "Crime Boss Support Plugin"
    Author = "modworkshop, MaskPlague and Silarn"
    Version = "1"
    GameName = "Crime Boss Rockay City"
    GameShortName = "crimeboss"
    GameSteamId = 2933080
    GameBinary = "CrimeBoss/Binaries/Win64/CrimeBoss-Win64-Shipping.exe"
    GameDataPath = "CrimeBoss"
    GameDataUE4SSMods = "Binaries/Win64/Mods"
    GameDataNativeMods = "Mods"
    GameDataPakMods = "Content/Paks/~Mods"
    GameDocumentsDirectory = "%USERPROFILE%/Saved Games/CrimeBoss/Steam/Saved/Config/WindowsNoEditor"
    GameSaveExtension = "sav"
    _main_window: QMainWindow
    _ue4ss_tab: UE4SSTabWidget
    _paks_tab: PaksTabWidget

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = CrimeBossModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        self._register_feature(CrimeBossModDataContent())
        organizer.onUserInterfaceInitialized(self.init_tab)
        return True

    def init_tab(self, main_window: QMainWindow):
        if self._organizer.managedGame() != self:
            return
        self._main_window = main_window
        tab_widget: QTabWidget = main_window.findChild(QTabWidget, "tabWidget")
        if not tab_widget or not tab_widget.findChild(QWidget, "espTab"):
            return
        self._ue4ss_tab = UE4SSTabWidget(main_window, self._organizer)
        plugin_tab = tab_widget.findChild(QWidget, "espTab")
        tab_index = tab_widget.indexOf(plugin_tab) + 1
        if not tab_widget.isTabVisible(tab_widget.indexOf(plugin_tab)):
            tab_index += 1
        tab_widget.insertTab(tab_index, self._ue4ss_tab, "UE4SS")
        self._paks_tab = PaksTabWidget(main_window, self._organizer)
        tab_index += 1
        tab_widget.insertTab(tab_index, self._paks_tab, "Paks")

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Crime Boss: Rockay City",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            )
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

    def paksDirectory(self) -> QDir:
        return QDir(self.dataDirectory().absolutePath() + "/" + self.GameDataPakMods)

    def ue4ssDirectory(self) -> QDir:
        return QDir(self.dataDirectory().absolutePath() + "/" + self.GameDataUE4SSMods)

    def nativeDirectory(self) -> QDir:
        return QDir(self.dataDirectory().absolutePath() + "/" + self.GameDataNativeMods)

    def write_default_mods(self, profile: QDir):
        ue4ss_mods_txt = QFileInfo(profile.absoluteFilePath("mods.txt"))
        ue4ss_mods_json = QFileInfo(profile.absoluteFilePath("mods.json"))
        if not ue4ss_mods_txt.exists():
            with open(ue4ss_mods_txt.absoluteFilePath(), "w") as mods_txt:
                for mod in DEFAULT_UE4SS_MODS:
                    mods_txt.write(f"{mod['mod_name']} : 1\n")
        if not ue4ss_mods_json.exists():
            mods_data: list[UE4SSModInfo] = []
            for mod in DEFAULT_UE4SS_MODS:
                mods_data.append({"mod_name": mod["mod_name"], "mod_enabled": True})
            with open(ue4ss_mods_json.absoluteFilePath(), "w") as mods_json:
                mods_json.write(json.dumps(mods_data, indent=4))

    def iniFiles(self):
        return ["GameUserSettings.ini", "Input.ini"]

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        self.write_default_mods(directory)
        if not self.paksDirectory().exists():
            os.makedirs(self.paksDirectory().absolutePath())
        if not self.ue4ssDirectory().exists():
            os.makedirs(self.ue4ssDirectory().absolutePath())
        if not self.nativeDirectory().exists():
            os.makedirs(self.nativeDirectory().absolutePath())
        super().initializeProfile(directory, settings)
