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
    QVBoxLayout,
)

import mobase

from ..basic_game import BasicGame


class Content(IntEnum):
    TEXTURE = auto()
    MESH = auto()
    SCRIPT = auto()
    SOUND = auto()
    STRING = auto()
    CONFIG = auto()


class Payday1ModDataContent(mobase.ModDataContent):
    content: list[int] = []
    GAMECONTENTS: list[tuple[Content, str, str, bool] | tuple[Content, str, str]] = [
        (Content.TEXTURE, "Textures", ":/MO/gui/content/texture"),
        (Content.MESH, "Meshes", ":/MO/gui/content/mesh"),
        (Content.SCRIPT, "Scripts", ":/MO/gui/content/script"),
        (Content.SOUND, "Sounds", ":/MO/gui/content/sound"),
        (Content.STRING, "Strings", ":/MO/gui/content/string"),
        (Content.CONFIG, "Configs", ":/MO/gui/content/inifile"),
    ]

    def getAllContents(self) -> list[mobase.ModDataContent.Content]:
        return [
            mobase.ModDataContent.Content(id, name, icon, *filter_only)
            for id, name, icon, *filter_only in self.GAMECONTENTS
        ]

    def walkContent(self, path: str, entry: mobase.FileTreeEntry):
        if entry.isFile():
            match entry.suffix().casefold():
                case "texture":
                    self.contents.append(Content.TEXTURE)
                case "model":
                    self.contents.append(Content.MESH)
                case "lua":
                    self.contents.append(Content.SCRIPT)
                case "stream":
                    self.contents.append(Content.SOUND)
                case "txt":
                    self.contents.append(Content.STRING)
                case "json":
                    self.contents.append(Content.CONFIG)
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


class Payday1ModDataChecker(mobase.ModDataChecker):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self.organizer: mobase.IOrganizer = organizer
        self.organizer.modList().onModInstalled(self.fixInstalledMod)
        self.needsNameFix = False
        self.modDetectionCandidates: list[ModDetectionCandidate] = []

    folderList = [
        "anims",
        "core",
        "effects",
        "environments",
        "fonts",
        "gamedata",
        "guis",
        "lib",
        "movies",
        "physic_effects",
        "settings",
        "shaders",
        "soundbanks",
        "strings",
        "units",
    ]

    def sanitizeFolderName(self, name: str) -> str:
        # Remove invalid characters for Windows folder names
        invalid_chars = '+&<>:"|?*\\/'
        for char in invalid_chars:
            name = name.replace(char, "")
        # Remove control characters (ASCII 0-31)
        name = "".join(c for c in name if ord(c) >= 32)
        # Remove trailing periods and spaces
        name = name.rstrip(". ")
        # If name is empty after sanitization, use a default
        if not name:
            name = "FOLDERNAME"
            self.needsNameFix = True
        return name

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

    def fixInstalledMod(self, mod: mobase.IModInterface):
        if not self.needsNameFix:
            return
        filetree: mobase.IFileTree = mod.fileTree()
        fixed = False
        modname = self.sanitizeFolderName(mod.name())
        if filetree.exists("mods/FOLDERNAME", mobase.IFileTree.DIRECTORY):
            path = mod.absolutePath()
            old_path = os.path.join(path, "mods/FOLDERNAME")
            new_path = os.path.join(path, f"mods/{modname}")
            self.moveOverwriteMerge(old_path, new_path)
            fixed = True
        elif filetree.exists(
            "assets/mod_overrides/FOLDERNAME", mobase.IFileTree.DIRECTORY
        ):
            path = mod.absolutePath()
            old_path = os.path.join(path, "assets/mod_overrides/FOLDERNAME")
            new_path = os.path.join(path, f"assets/mod_overrides/{modname}")
            self.moveOverwriteMerge(old_path, new_path)
            fixed = True
        elif filetree.exists("maps/FOLDERNAME", mobase.IFileTree.DIRECTORY):
            path = mod.absolutePath()
            old_path = os.path.join(path, "maps/FOLDERNAME")
            new_path = os.path.join(path, f"maps/{modname}")
            self.moveOverwriteMerge(old_path, new_path)
            fixed = True
        if not fixed:
            return
        self.needsNameFix = False

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        validList = {"assets", "mods", "maps"}
        for e in filetree:
            if isinstance(e, mobase.IFileTree) and e.isDir():
                if e.name().casefold() not in validList:
                    return mobase.ModDataChecker.FIXABLE
        if filetree.exists("assets/mod_overrides", mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        if filetree.exists("mods", mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        if filetree.exists("maps", mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        if filetree.exists("IPHLPAPI.dll", mobase.IFileTree.FILE):
            return mobase.ModDataChecker.VALID
        if filetree.exists("WSOCK32.dll", mobase.IFileTree.FILE):
            return mobase.ModDataChecker.VALID
        if filetree.exists("DINPUT8.dll", mobase.IFileTree.FILE):
            return mobase.ModDataChecker.VALID
        if filetree.exists("PDTHModOverrides.dll", mobase.IFileTree.FILE):
            return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.FIXABLE

    def moveTreeContent(
        self,
        sourcetree: mobase.IFileTree,
        targettree: mobase.IFileTree,
        destination: str,
    ) -> bool:
        entriesToMove: list[mobase.FileTreeEntry] = []
        for e in sourcetree:
            entriesToMove.append(e)
        for e in entriesToMove:
            targettree.move(e, destination, mobase.IFileTree.MERGE)
        targettree.remove(sourcetree)
        return bool(entriesToMove)

    def addModDetectionCandidate(
        self,
        tree: mobase.IFileTree,
        name: str,
        category: str,
        destination: str,
    ) -> None:
        tree_name = tree.name()
        tree_path = tree.path()

        print(
            f"Detected mod candidate: {tree_name} | "
            f"path={tree_path} | category={category} | destination={destination}"
        )
        self.modDetectionCandidates.append(
            {
                "tree": tree,
                "name": tree_name,
                "display": f"{name} ({category})",
                "destination": destination,
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
        self, tree: mobase.IFileTree | mobase.FileTreeEntry
    ) -> bool:
        if isinstance(tree, mobase.IFileTree):
            sanitizedName = self.sanitizeFolderName(tree.name())
            hasDisallowedPath = False
            disallowedFolders = {"assets", "levels", "lua", "map_replacements"}
            tree_path = tree.path()
            tree_path_lower = tree_path.replace("\\", "/").casefold()
            if disallowedFolders & set(tree_path_lower.split("/")):
                hasDisallowedPath = True
            hasFolderListSubfolder = any(
                tree.exists(validFolder, mobase.IFileTree.DIRECTORY)
                for validFolder in self.folderList
            )
            if not hasDisallowedPath:
                if (
                    tree.exists("mod.txt", mobase.IFileTree.FILE)
                    and not hasFolderListSubfolder
                ):
                    self.addModDetectionCandidate(
                        tree,
                        self.sanitizeFolderName(tree.name()),
                        "BLT",
                        "mods/" + sanitizedName + "/",
                    )
                    return True
                elif tree.exists("main.xml", mobase.IFileTree.FILE) and tree.exists(
                    "levels", mobase.IFileTree.DIRECTORY
                ):
                    self.addModDetectionCandidate(
                        tree,
                        self.sanitizeFolderName(tree.name()),
                        "Map Core",
                        "maps/" + sanitizedName + "/",
                    )
                    return True
                elif (
                    tree.exists("main.xml", mobase.IFileTree.FILE)
                    or tree.exists("add.xml", mobase.IFileTree.FILE)
                    or tree.exists("supermod.xml", mobase.IFileTree.FILE)
                ):
                    self.addModDetectionCandidate(
                        tree,
                        self.sanitizeFolderName(tree.name()),
                        "SuperBLT",
                        "assets/mod_overrides/" + sanitizedName + "/",
                    )
                    return True
                else:
                    for validFolder in self.folderList:
                        if tree.exists(validFolder, mobase.IFileTree.DIRECTORY):
                            self.addModDetectionCandidate(
                                tree,
                                self.sanitizeFolderName(tree.name()),
                                "Override",
                                "assets/mod_overrides/" + sanitizedName + "/",
                            )
                            return True
        return False

    def walkEntry(self, path: str, entry: mobase.FileTreeEntry):
        if entry.isDir():
            if isinstance(entry, mobase.IFileTree):
                self.collectModCandidates(entry)
        return mobase.IFileTree.WalkReturn.CONTINUE

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree | None:
        self.modDetectionCandidates = []
        newtree = filetree.createOrphanTree("Fixed Tree")
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
            if isinstance(candidate["tree"], mobase.IFileTree):
                print(
                    f"Installing Mod: {candidate['name']} to {candidate['destination']}"
                )
                if self.moveTreeContent(
                    candidate["tree"], newtree, candidate["destination"]
                ):
                    self.needsNameFix = True

        return newtree if len(newtree) > 0 else filetree


class Payday1Game(BasicGame):
    Name = "Payday 1 Support Plugin"
    Author = "ModWorkshop"
    CategorySource = "modworkshop"
    Version = "1"
    GameName = "Payday: The Heist"
    GameShortName = "pdth"
    GameSteamId = 24240
    GameBinary = "payday_win32_release.exe"
    GameDataPath = "%GAME_PATH%"
    GameDocumentsDirectory = "%USERPROFILE%/AppData/Local/PAYDAY"
    _forced_libraries = [
        "IPHLPAPI.dll",
        "WSOCK32.dll",
        "DINPUT8.dll",
        "PDTHModOverrides.dll",
    ]

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = Payday1ModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        self._register_feature(Payday1ModDataContent())
        organizer.modList().onModStateChanged(self.dllCopy)
        return True

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Payday the Heist",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            )
        ]

    def dllCopy(self, mods: dict[str, mobase.ModState]):
        game_path = self.dataDirectory().absolutePath() + "/"

        for key, value in mods.items():
            key = self._organizer.modList().getMod(key)
            tree = key.fileTree()
            for e in tree:
                if e.name() in self._forced_libraries:
                    # add file
                    file_path_source = key.absolutePath() + "/" + e.path()
                    file_path_target = game_path + e.name()
                    if value == 35:
                        shutil.copyfile(file_path_source, file_path_target)
                    # remove file
                    if value == 33:
                        if os.path.exists(file_path_target):
                            os.remove(file_path_target)

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

    def iniFiles(self):
        return ["renderer_settings.xml"]

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        base_data_dir = self.dataDirectory().absolutePath()

        mapsDirectory = QDir(base_data_dir + "/maps")
        modsDirectory = QDir(base_data_dir + "/mods")
        overridesDirectory = QDir(base_data_dir + "/assets/mod_overrides")

        if not mapsDirectory.exists():
            os.makedirs(mapsDirectory.absolutePath())
        if not modsDirectory.exists():
            os.makedirs(modsDirectory.absolutePath())
        if not overridesDirectory.exists():
            os.makedirs(overridesDirectory.absolutePath())
        super().initializeProfile(directory, settings)
