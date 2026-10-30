import os
import shutil
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


class ModDetectionCandidate(TypedDict):
    tree: mobase.IFileTree | mobase.FileTreeEntry
    display: str


class RoadToVostokModDataChecker(mobase.ModDataChecker):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self.organizer: mobase.IOrganizer = organizer
        self.modDetectionCandidates: list[ModDetectionCandidate] = []

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
        return name

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        if filetree.exists("mods", mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.FIXABLE

    def moveTreeContent(
        self,
        filetree: mobase.IFileTree,
        file: mobase.IFileTree | mobase.FileTreeEntry,
    ) -> None:
        GameModsPath = getattr(self.organizer.managedGame(), "GameModsPath", "") + "/"
        if filetree.name() == "":
            filetree.move(file, GameModsPath, mobase.IFileTree.MERGE)
        else:
            mod_name = filetree.name()
            mod_file = file.name()
            mod_path = os.path.join(self.organizer.modsPath(), mod_name)
            insideMods = os.path.join(mod_path, GameModsPath)
            os.makedirs(insideMods, exist_ok=True)
            src = os.path.join(mod_path, mod_file)
            dst = os.path.join(mod_path, GameModsPath, mod_file)
            shutil.move(
                src,
                dst,
            )
        return None

    def addModDetectionCandidate(
        self,
        tree: mobase.IFileTree | mobase.FileTreeEntry,
        name: str,
        category: str,
    ) -> None:
        self.modDetectionCandidates.append(
            {
                "tree": tree,
                "display": f"{name} ({category})",
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
        if os.path.splitext(tree.path())[1].removeprefix(".") == "vmz":
            self.addModDetectionCandidate(
                tree,
                self.sanitizeFolderName(tree.name()),
                "VMZ Archive",
            )
            return True
        return False

    def walkEntry(self, path: str, entry: mobase.FileTreeEntry):
        self.collectModCandidates(entry)
        return mobase.IFileTree.WalkReturn.CONTINUE

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree | None:
        self.modDetectionCandidates = []

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
            self.moveTreeContent(filetree, candidate["tree"])

        return filetree


class RoadToVostokGame(BasicGame):
    Name = "Road to Vostok Support Plugin"
    Author = "ModWorkshop"
    CategorySource = "modworkshop"
    Version = "1"
    GameName = "Road to Vostok"
    GameShortName = "roadtovostok"
    GameSteamId = 1963610
    GameBinary = "RTV.exe"
    GameModsPath = "mods"
    GameDataPath = "%GAME_PATH%"
    GameDocumentsDirectory = "%USERPROFILE%/AppData/Roaming/Road to Vostok"
    GameSaveExtension = "tres"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = RoadToVostokModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        return True

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Road to Vostok",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
        ]

    def iniFiles(self):
        return ["settings.cfg"]

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        modsPath = self.dataDirectory().absolutePath() + "/mods"
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)
        super().initializeProfile(directory, settings)
