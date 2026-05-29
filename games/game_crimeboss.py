import json
import os
import shutil
from enum import IntEnum, auto
from functools import cached_property
from pathlib import Path
from typing import TypedDict

from PyQt6.QtCore import QDir, QFileInfo, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import mobase

from ..basic_game import BasicGame
from .unreal_tabs.constants import DEFAULT_UE4SS_MODS, UE4SSModInfo
from .unreal_tabs.manage_paks.widget import PaksTabWidget
from .unreal_tabs.manage_ue4ss.widget import UE4SSTabWidget


class Content(IntEnum):
    UCAS = auto()
    UTOC = auto()
    PAK = auto()
    UE4SS = auto()
    DLL = auto()
    BK2 = auto()


class CrimeBossModDataContent(mobase.ModDataContent):
    content: list[int] = []
    GAMECONTENTS: list[tuple[Content, str, str, bool] | tuple[Content, str, str]] = [
        (Content.UCAS, "UCAS", ":/MO/gui/content/geometries"),
        (Content.UTOC, "UTOC", ":/MO/gui/content/inifile"),
        (Content.PAK, "PAK", ":/MO/gui/content/geometries"),
        (Content.UE4SS, "UE4SS", ":/MO/gui/content/script"),
        (Content.DLL, "DLL", ":/MO/gui/content/skse"),
        (Content.BK2, "Video", ":/MO/gui/content/modgroup"),
    ]

    def getAllContents(self) -> list[mobase.ModDataContent.Content]:
        return [
            mobase.ModDataContent.Content(id, name, icon, *filter_only)
            for id, name, icon, *filter_only in self.GAMECONTENTS
        ]

    def walkContent(self, path: str, entry: mobase.FileTreeEntry):
        if entry.isFile():
            match entry.suffix().casefold():
                case "utoc":
                    self.contents.append(Content.UTOC)
                case "ucas":
                    self.contents.append(Content.UCAS)
                case "pak":
                    self.contents.append(Content.PAK)
                case "lua":
                    self.contents.append(Content.UE4SS)
                case "dll":
                    self.contents.append(Content.DLL)
                case "bk2":
                    self.contents.append(Content.BK2)
                case _:
                    pass
        return mobase.IFileTree.WalkReturn.CONTINUE

    def getContentsFor(self, filetree: mobase.IFileTree) -> list[int]:
        self.contents: list[int] = []
        filetree.walk(self.walkContent, "/")
        return list(self.contents)


class ModDetectionCandidate(TypedDict):
    tree: mobase.IFileTree | mobase.FileTreeEntry
    name: str
    display: str
    destination: str
    installtype: str


class CrimeBossModDataChecker(mobase.ModDataChecker):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self.organizer: mobase.IOrganizer = organizer
        self.organizer.modList().onModInstalled(self.fixInstalledMod)
        self.needsNameFix = False
        self.modDetectionCandidates: list[ModDetectionCandidate] = []

    def moveOverwriteMerge(self, source: str, destination: str):
        if not os.path.exists(destination):
            shutil.move(source, destination)
            return
        if os.path.isfile(source):
            os.replace(source, destination)
            return
        for item in os.listdir(source):
            s_item = os.path.join(source, item)
            d_item = os.path.join(destination, item)
            self.moveOverwriteMerge(s_item, d_item)
        os.rmdir(source)

    def sanitizeFolderName(self, name: str) -> str:
        invalid_chars = '+&<>:"|?*\\/'
        for char in invalid_chars:
            name = name.replace(char, "")
        name = "".join(c for c in name if ord(c) >= 32)
        name = name.rstrip(". ")
        if not name:
            name = "FOLDERNAME"
        return name

    def fixInstalledMod(self, mod: mobase.IModInterface):
        if not self.needsNameFix:
            return
        GameDataNativeMods = getattr(
            self.organizer.managedGame(), "GameDataNativeMods", ""
        )
        filetree: mobase.IFileTree = mod.fileTree()
        fixed = False
        modname = mod.name()
        if filetree.exists(
            GameDataNativeMods + "/FOLDERNAME", mobase.IFileTree.DIRECTORY
        ):
            path = mod.absolutePath()
            old_path = os.path.join(path, GameDataNativeMods + "/FOLDERNAME")
            new_path = os.path.join(path, GameDataNativeMods + f"/{modname}")
            self.moveOverwriteMerge(old_path, new_path)
            fixed = True
        if not fixed:
            return
        self.needsNameFix = False

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        GameDataUE4SSMods = getattr(
            self.organizer.managedGame(), "GameDataUE4SSMods", ""
        )
        GameDataPakMods = getattr(self.organizer.managedGame(), "GameDataPakMods", "")
        GameDataNativeMods = getattr(
            self.organizer.managedGame(), "GameDataNativeMods", ""
        )
        GameDataMovies = getattr(self.organizer.managedGame(), "GameDataMovies", "")
        if filetree.exists(GameDataPakMods, mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        if filetree.exists(GameDataMovies, mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        if filetree.exists(GameDataUE4SSMods, mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        if filetree.exists(GameDataNativeMods, mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.FIXABLE

    def moveTreeContent(
        self,
        installtype: str,
        entry: mobase.IFileTree | mobase.FileTreeEntry,
        targettree: mobase.IFileTree,
        destination: str,
    ) -> None:
        if installtype == "virtual":
            targettree.move(entry, destination, mobase.IFileTree.MERGE)
            return None
        if installtype == "os" and isinstance(entry, mobase.IFileTree):
            for element in entry:
                mod_file = element.name()
                mod_name = entry.name()
                mod_path = os.path.join(self.organizer.modsPath(), mod_name)
                inside_mods = os.path.join(mod_path, destination)
                os.makedirs(inside_mods, exist_ok=True)
                src = os.path.join(mod_path, mod_file)
                dst = os.path.join(mod_path, destination, mod_file)
                shutil.move(src, dst)
            return None

    def addModDetectionCandidate(
        self,
        tree: mobase.IFileTree | mobase.FileTreeEntry,
        name: str,
        category: str,
        destination: str,
        installtype: str = "virtual",
    ) -> None:
        self.modDetectionCandidates.append(
            {
                "tree": tree,
                "name": tree.name(),
                "display": f"{name} ({category})",
                "destination": destination,
                "installtype": installtype,
            }
        )

    def showModDetectionDialog(self) -> set[int] | None:
        if not self.modDetectionCandidates:
            return set()

        dialog = QDialog()
        dialog.setWindowTitle("Found Mods")

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select the mods to install:"))

        listWidget = QListWidget()
        listWidget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        for candidate in self.modDetectionCandidates:
            item = QListWidgetItem(candidate["display"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            listWidget.addItem(item)

        layout.addWidget(listWidget)

        buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttonBox.accepted.connect(lambda: dialog.accept())  # type: ignore
        buttonBox.rejected.connect(lambda: dialog.reject())  # type: ignore
        layout.addWidget(buttonBox)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        selectedIndexes: set[int] = set()
        for index in range(listWidget.count()):
            item = listWidget.item(index)
            if (
                isinstance(item, QListWidgetItem)
                and item.checkState() == Qt.CheckState.Checked
            ):
                selectedIndexes.add(index)

        return selectedIndexes

    def collectModCandidates(
        self,
        tree: mobase.IFileTree | mobase.FileTreeEntry,
        installtype: str = "virtual",
    ) -> bool:
        if not isinstance(tree, mobase.IFileTree) or not tree.name():
            return False

        sanitized_name = self.sanitizeFolderName(tree.name())
        category = None
        entryext = "None"

        GameDataUE4SSRootDir = getattr(
            self.organizer.managedGame(), "GameDataUE4SSMods", ""
        )
        GameDataPakModsDir = getattr(
            self.organizer.managedGame(), "GameDataPakMods", ""
        )
        GameDataNativeModsDir = getattr(
            self.organizer.managedGame(), "GameDataNativeMods", ""
        )
        GameDataMoviesDir = getattr(self.organizer.managedGame(), "GameDataMovies", "")

        if installtype == "os" and isinstance(tree, mobase.IFileTree):
            for entry in tree:
                entryext = os.path.splitext(entry.name())[1].removeprefix(".")
        else:
            entryext = tree.suffix().casefold()

        # Check for UE4SS installations
        if isinstance(tree, mobase.IFileTree) and tree.isDir():
            if tree.exists("ue4ss.dll", mobase.IFileTree.FILE) or tree.exists(
                "dsound.dll", mobase.IFileTree.FILE
            ):
                category = "Root"
            elif tree.exists("Scripts", mobase.IFileTree.DIRECTORY) and not tree.exists(
                "UE4SS.dll", mobase.IFileTree.FILE
            ):
                disallowedFolders = {"mods"}
                tree_path = tree.path()
                tree_path_lower = tree_path.replace("\\", "/").casefold()
                if not disallowedFolders & set(tree_path_lower.split("/")):
                    category = "UE4SS"
            elif tree.exists("Content", mobase.IFileTree.DIRECTORY):
                category = "Native"

        # Check single file for correct extensions
        match entryext:
            case "pak" | "utoc" | "ucas":
                category = "Paks"
            case "bk2":
                category = "Movie"
            case _:
                pass

        if category is None:
            return False

        if category == "UE4SS":
            destination = GameDataUE4SSRootDir + "/"
        elif category == "Root":
            destination = GameDataUE4SSRootDir + "/"
        elif category == "Paks":
            destination = GameDataPakModsDir + "/"
        elif category == "Movie":
            destination = GameDataMoviesDir + "/"
        elif category == "Native":
            destination = GameDataNativeModsDir + "/"
        else:
            destination = "/"

        self.addModDetectionCandidate(
            tree,
            sanitized_name,
            f"{category} Mod",
            destination,
            installtype,
        )
        return True

    def walkEntry(self, path: str, entry: mobase.FileTreeEntry):
        if entry.isDir() and isinstance(entry, mobase.IFileTree):
            self.collectModCandidates(entry)
        return mobase.IFileTree.WalkReturn.CONTINUE

    def fileExistsInNextSubDir(self, filetree: mobase.IFileTree, name: str):
        for branch in filetree:
            if isinstance(branch, mobase.IFileTree):
                for e in branch:
                    if e.name() == name:
                        return True
        return False

    def allMoveTo(self, filetree: mobase.IFileTree, toMoveTo: str):
        entriesToMove: list[mobase.FileTreeEntry] = []
        retVal = 0
        for e in filetree:
            entriesToMove.append(e)
        for e in entriesToMove:
            filetree.move(e, toMoveTo, mobase.IFileTree.MERGE)
            retVal = 1
        return retVal

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree | None:
        self.modDetectionCandidates = []
        newtree = filetree.createOrphanTree("Fixed Tree")

        # Check for Non Zipped Mod
        if filetree.name() != "":
            self.collectModCandidates(filetree, installtype="os")
        else:
            self.collectModCandidates(filetree)
            filetree.walk(self.walkEntry, "/")

        if len(self.modDetectionCandidates) == 1:
            selectedIndexes = {0}
        else:
            selectedIndexes = self.showModDetectionDialog()
            if selectedIndexes is None:
                return None

        for index in selectedIndexes:
            candidate = self.modDetectionCandidates[index]
            self.moveTreeContent(
                candidate["installtype"],
                candidate["tree"],
                newtree,
                candidate["destination"],
            )

        if newtree:
            return newtree

        # Fallback: Handle native mods with FOLDERNAME substitution
        GameDataNativeMods = getattr(
            self.organizer.managedGame(), "GameDataNativeMods", ""
        )
        if filetree.exists("Content", mobase.IFileTree.DIRECTORY):
            self.needsNameFix = True
            self.allMoveTo(filetree, GameDataNativeMods + "/FOLDERNAME/")
            return filetree

        return filetree


class CrimeBossGame(BasicGame):
    Name = "Crime Boss Support Plugin"
    Author = "ModWorkshop, MaskPlague and Silarn"
    CategorySource = "modworkshop"
    Version = "1"
    GameName = "Crime Boss Rockay City"
    GameShortName = "crimeboss"
    GameSteamId = 2933080
    GameBinary = "CrimeBoss/Binaries/Win64/CrimeBoss-Win64-Shipping.exe"
    GameDataPath = "CrimeBoss"
    GameDataUE4SSRoot = "Binaries/Win64"
    GameDataNativeMods = "Mods"
    GameDataPakMods = "Content/Paks/~Mods"
    GameDocumentsDirectory = (
        "%USERPROFILE%/Saved Games/CrimeBoss/Steam/Saved/Config/WindowsNoEditor"
    )
    GameSaveExtension = "sav"
    _main_window: QMainWindow
    _ue4ss_tab: UE4SSTabWidget
    _paks_tab: PaksTabWidget

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = CrimeBossModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        self._register_feature(CrimeBossModDataContent())
        organizer.onUserInterfaceInitialized(self.initTab)
        return True

    def initTab(self, main_window: QMainWindow):
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

    def paksDirectory(self) -> QDir:
        return QDir(self.dataDirectory().absolutePath() + "/" + self.GameDataPakMods)

    def ue4ssDirectory(self) -> QDir:
        return QDir(
            self.dataDirectory().absolutePath() + "/" + self.GameDataUE4SSRoot + "/Mods"
        )

    def nativeDirectory(self) -> QDir:
        return QDir(self.dataDirectory().absolutePath() + "/" + self.GameDataNativeMods)

    def writeDefaultMods(self, profile: QDir):
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
        self.writeDefaultMods(directory)
        if not self.paksDirectory().exists():
            os.makedirs(self.paksDirectory().absolutePath())
        if not self.ue4ssDirectory().exists():
            os.makedirs(self.ue4ssDirectory().absolutePath())
        if not self.nativeDirectory().exists():
            os.makedirs(self.nativeDirectory().absolutePath())
        super().initializeProfile(directory, settings)
