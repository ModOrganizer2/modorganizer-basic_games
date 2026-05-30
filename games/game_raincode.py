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
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
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


class RainCodePlusModDataContent(mobase.ModDataContent):
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
    trees: list[mobase.IFileTree | mobase.FileTreeEntry]
    name: str
    display: str
    destination: str
    installtype: str


class RainCodePlusModDataChecker(mobase.ModDataChecker):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self.organizer: mobase.IOrganizer = organizer
        self.modDetectionCandidates: list[ModDetectionCandidate] = []
        self.processedBasenames: set[str] = set()  # Track already-grouped files
        self.category_groups: dict[str, list[mobase.FileTreeEntry]] = {}

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
            name = "Mod"
        return name

    def groupRelatedFiles(
        self,
        entries: list[mobase.FileTreeEntry],
    ) -> list[list[mobase.FileTreeEntry]]:
        """Group files that belong together (e.g., .pak, .utoc, .ucas with same base name)."""
        grouped: dict[str, list[mobase.FileTreeEntry]] = {}

        for entry in entries:
            # Get base name without extension
            name_without_ext = os.path.splitext(entry.name())[0]
            if name_without_ext not in grouped:
                grouped[name_without_ext] = []
            grouped[name_without_ext].append(entry)

        return list(grouped.values())

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        GameDataUE4SSMods = getattr(
            self.organizer.managedGame(), "GameDataUE4SSRoot", ""
        )
        GameDataPakMods = getattr(self.organizer.managedGame(), "GameDataPakMods", "")
        GameDataMovieMods = getattr(
            self.organizer.managedGame(), "GameDataMovieMods", ""
        )
        if filetree.exists(GameDataPakMods, mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        if filetree.exists(GameDataMovieMods, mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        if filetree.exists(GameDataUE4SSMods, mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.FIXABLE

    def moveTreeContent(
        self,
        installtype: str,
        entries: list[mobase.IFileTree | mobase.FileTreeEntry],
        targettree: mobase.IFileTree,
        destination: str,
    ) -> None:
        if installtype == "virtual":
            for entry in entries:
                targettree.move(entry, destination, mobase.IFileTree.MERGE)
        elif installtype == "os":
            entry = entries[0]
            for subentry in entry:
                mod_file = subentry.name()
                mod_name_val = entry.name()
                mod_path = os.path.join(self.organizer.modsPath(), mod_name_val)
                insideMods = os.path.join(mod_path, destination)
                os.makedirs(insideMods, exist_ok=True)
                src = os.path.join(mod_path, mod_file)
                dst = os.path.join(mod_path, destination, mod_file)
                shutil.move(
                    src,
                    dst,
                )
            return None

    def addModDetectionCandidate(
        self,
        trees: list[mobase.IFileTree | mobase.FileTreeEntry],
        name: str,
        category: str,
        destination: str,
        installtype: str,
    ) -> None:
        tree_name = self.sanitizeFolderName(trees[0].name() if trees else "Unknown")

        self.modDetectionCandidates.append(
            {
                "trees": trees,
                "name": tree_name,
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

        selectButtons = QHBoxLayout()
        selectAllButton = QPushButton("Select All")
        selectNoneButton = QPushButton("Select None")
        selectAllButton.clicked.connect(
            lambda: self.setDialogSelection(listWidget, True)
        )  # type: ignore
        selectNoneButton.clicked.connect(
            lambda: self.setDialogSelection(listWidget, False)
        )  # type: ignore
        selectButtons.addWidget(selectAllButton)
        selectButtons.addWidget(selectNoneButton)
        layout.addLayout(selectButtons)

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

    def setDialogSelection(self, listWidget: QListWidget, select: bool) -> None:
        state = Qt.CheckState.Checked if select else Qt.CheckState.Unchecked
        for index in range(listWidget.count()):
            item = listWidget.item(index)
            if isinstance(item, QListWidgetItem):
                item.setCheckState(state)

    def collectModCandidates(
        self,
        path: str,
        entry: mobase.FileTreeEntry,
        installtype: str = "virtual",
    ):
        category = None
        entryext = "None"
        basename = "Unknown"
        GameDataUE4SSRootDir = getattr(
            self.organizer.managedGame(), "GameDataUE4SSRoot", ""
        )
        GameDataUE4SSModsDir = GameDataUE4SSRootDir + "/Mods"
        GameDataPakModsDir = getattr(
            self.organizer.managedGame(), "GameDataPakMods", ""
        )
        GameDataMovieModsDir = getattr(
            self.organizer.managedGame(), "GameDataMovieMods", ""
        )

        if installtype == "os" and isinstance(entry, mobase.IFileTree):
            for subentry in entry:
                entryext = os.path.splitext(subentry.name())[1].removeprefix(".")
                basename = os.path.splitext(subentry.name())[0]
        else:
            entryext = entry.suffix().casefold()
            basename = os.path.splitext(entry.name())[0]

        if isinstance(entry, mobase.IFileTree) and entry.isDir():
            if entry.exists("ue4ss.dll", mobase.IFileTree.FILE) or entry.exists(
                "dsound.dll", mobase.IFileTree.FILE
            ):
                category = "Root"
            elif entry.exists(
                "Scripts", mobase.IFileTree.DIRECTORY
            ) and not entry.exists("ue4ss.dll", mobase.IFileTree.FILE):
                disallowedFolders = {"mods"}
                tree_path = entry.path()
                tree_path_lower = tree_path.replace("\\", "/").casefold()
                if not disallowedFolders & set(tree_path_lower.split("/")):
                    category = "UE4SS"

        # Check single file for correct extentions
        match entryext:
            case "pak" | "utoc" | "ucas":
                category = "Paks"
            case "bk2":
                category = "Movie"
            case _:
                pass

        if category is not None:
            basename = basename + " " + category

            if basename not in self.category_groups:
                self.category_groups[basename] = []

            self.category_groups[basename].append(entry)

            # Add grouped entries as candidates
            for basename, entries in self.category_groups.items():
                if basename not in self.processedBasenames:
                    self.processedBasenames.add(basename)
                    sanitized_name = self.sanitizeFolderName(entries[0].name())

                    if category == "UE4SS":
                        destination = GameDataUE4SSModsDir + "/"
                    elif category == "Root":
                        destination = GameDataUE4SSRootDir + "/"
                    elif category == "Paks":
                        destination = GameDataPakModsDir + "/"
                    elif category == "Movie":
                        destination = GameDataMovieModsDir + "/"
                    else:
                        destination = "/"

                    if installtype == "os":
                        # Single file/entry
                        self.addModDetectionCandidate(
                            [entry],
                            sanitized_name,
                            f"{category} Mod",
                            destination,
                            installtype,
                        )
                    else:
                        candidate_entries = entries

                        if category == "Root":
                            candidate_entries = []
                            for root_entry in entries:
                                if root_entry.isDir():
                                    candidate_entries.extend(list(root_entry))
                                else:
                                    candidate_entries.append(root_entry)

                        self.addModDetectionCandidate(
                            candidate_entries,
                            sanitized_name,
                            f"{category} Mod",
                            destination,
                            installtype,
                        )

        return mobase.IFileTree.WalkReturn.CONTINUE

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree | None:
        self.modDetectionCandidates = []
        self.processedBasenames = set()
        self.category_groups = {}
        UnZippedInstallation = False
        newtree = filetree.createOrphanTree("Fixed Tree")

        if filetree.name() != "":
            # Initial Check on Main Directory
            self.collectModCandidates("/", filetree, installtype="os")
            UnZippedInstallation = True
        else:
            # Initial Check on Main Directory
            self.collectModCandidates("/", filetree)
            filetree.walk(self.collectModCandidates, "/")

        if len(self.modDetectionCandidates) == 1:
            selectedIndexes = {0}
        else:
            selectedIndexes = self.showModDetectionDialog()
            if selectedIndexes is None:
                return None

        if not UnZippedInstallation:
            filetree = newtree

        for index in selectedIndexes:
            candidate = self.modDetectionCandidates[index]
            self.moveTreeContent(
                candidate["installtype"],
                candidate["trees"],
                filetree,
                candidate["destination"],
            )

        return filetree


class RainCodePlusGame(BasicGame):
    Name = "Master Detective Archives: RAIN CODE Plus Support Plugin"
    Author = "ModWorkshop"
    CategorySource = "modworkshop"
    Version = "1"
    GameLauncher = "RainCodePlus.exe"
    GameName = "Master Detective Archives: RAIN CODE Plus"
    GameShortName = "masterdetectivearchivesraincodeplus"
    GameSteamId = 903950
    GameBinary = "RainCodePlus/Binaries/Win64/RainCodePlus-Win64-Shipping.exe"
    GameDataPath = "RainCodePlus"
    GameDataUE4SSRoot = "Binaries/Win64"
    GameDataPakMods = "Content/Paks/~Mods"
    GameDataMovieMods = "Content/Movies"
    GameDocumentsDirectory = "%LOCALAPPDATA%/RainCodePlus/Saved/Config/Windows"
    GameSavesDirectory = "%LOCALAPPDATA%/RainCodePlus/Saved/SaveGames"
    GameSaveExtension = "sav"
    _main_window: QMainWindow
    _ue4ss_tab: UE4SSTabWidget
    _paks_tab: PaksTabWidget

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = RainCodePlusModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        self._register_feature(RainCodePlusModDataContent())
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
                "Master Detective Archives: RAIN CODE Plus",
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
        return ["GameUserSettings.ini", "Engine.ini"]

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        self.writeDefaultMods(directory)

        base_data_dir = self.dataDirectory().absolutePath()

        paksDirectory = QDir(base_data_dir + "/" + self.GameDataPakMods)
        ue4ssDirectory = QDir(base_data_dir + "/" + self.GameDataUE4SSRoot + "/Mods")
        movieDirectory = QDir(base_data_dir + "/" + self.GameDataMovieMods)

        if not paksDirectory.exists():
            os.makedirs(paksDirectory.absolutePath())
        if not ue4ssDirectory.exists():
            os.makedirs(ue4ssDirectory.absolutePath())
        if not movieDirectory.exists():
            os.makedirs(movieDirectory.absolutePath())
        super().initializeProfile(directory, settings)
