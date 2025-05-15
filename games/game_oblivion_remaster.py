import json
import os.path
import shutil
import winreg
from enum import IntEnum, auto
from functools import cmp_to_key
from pathlib import Path
from typing import Any, Sequence

from PyQt6.QtCore import (
    QByteArray,
    QCoreApplication,
    QDateTime,
    QDir,
    QFile,
    QFileInfo,
    QMimeData,
    QModelIndex,
    QStandardPaths,
    QStringConverter,
    QStringEncoder,
    QStringListModel,
    Qt,
    pyqtSignal,
    qCritical,
    qWarning,
)
from PyQt6.QtGui import QDropEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QListView,
    QMainWindow,
    QTabWidget,
    QWidget,
)

import mobase

from ..basic_features import BasicGameSaveGameInfo
from ..basic_features.utils import is_directory
from ..basic_game import BasicGame

DEFAULT_UE4SS_MODS = ["BPML_GenericFunctions", "BPModLoaderMod"]


def getLootPath() -> Path | None:
    paths = [
        (
            winreg.HKEY_CURRENT_USER,
            "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{BF634210-A0D4-443F-A657-0DCE38040374}_is1",
            "InstallLocation",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{BF634210-A0D4-443F-A657-0DCE38040374}_is1",
            "InstallLocation",
        ),
        (winreg.HKEY_LOCAL_MACHINE, "Software\\LOOT", "Installed Path"),
    ]

    for path in paths:
        try:
            with winreg.OpenKeyEx(
                path[0],
                path[1],
            ) as key:
                value = winreg.QueryValueEx(key, path[2])
                return Path((value[0] + "/LOOT.exe").replace("/", "\\"))
        except FileNotFoundError:
            pass
    return None


class Content(IntEnum):
    PLUGIN = auto()
    BSA = auto()
    PAK = auto()
    OBSE = auto()
    OBSE_FILES = auto()
    MOVIE = auto()
    UE4SS = auto()
    MAGIC_LOADER = auto()


class Problems(IntEnum):
    UE4SS_LOADER = auto()


class UE4SSListModel(QStringListModel):
    def __init__(self, parent: QWidget | None, organizer: mobase.IOrganizer):
        super().__init__(parent)
        self._checked_items: set[str] = set()
        self._organizer = organizer
        self._init_mod_states()

    def _init_mod_states(self):
        profile = QDir(self._organizer.profilePath())
        mods_json = QFileInfo(profile.absoluteFilePath("mods.json"))
        if mods_json.exists():
            with open(mods_json.absoluteFilePath(), "r") as json_file:
                mod_data = json.load(json_file)
                for mod in mod_data:
                    if mod["mod_enabled"]:
                        self._checked_items.add(mod["mod_name"])

    def _set_mod_states(self):
        profile = QDir(self._organizer.profilePath())
        mods_json = QFileInfo(profile.absoluteFilePath("mods.json"))
        mod_list: dict[str, bool] = {}
        if mods_json.exists():
            with open(mods_json.absoluteFilePath(), "r") as json_file:
                mod_data = json.load(json_file)
                for mod in mod_data:
                    mod_list[mod["mod_name"]] = mod["mod_enabled"]
            for i in range(self.rowCount()):
                item = self.index(i, 0)
                name = self.data(item, Qt.ItemDataRole.DisplayRole)
                if name in mod_list:
                    self.setData(
                        item,
                        True if mod_list[name] else False,
                        Qt.ItemDataRole.CheckStateRole,
                    )
                else:
                    self.setData(item, True, Qt.ItemDataRole.CheckStateRole)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        if not index.isValid():
            return (
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
                | Qt.ItemFlag.ItemIsDropEnabled
                | Qt.ItemFlag.ItemIsEnabled
            )
        return (
            flags
            | Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsDragEnabled & Qt.ItemFlag.ItemIsEditable
        )

    def setData(self, index: QModelIndex, value: Any, role: int = ...) -> bool:
        if not index.isValid() or role != Qt.ItemDataRole.CheckStateRole:
            return False

        if (
            bool(value)
            and self.data(index, Qt.ItemDataRole.DisplayRole) not in self._checked_items
        ):
            self._checked_items.add(self.data(index, Qt.ItemDataRole.DisplayRole))
        elif (
            not bool(value)
            and self.data(index, Qt.ItemDataRole.DisplayRole) in self._checked_items
        ):
            self._checked_items.remove(self.data(index, Qt.ItemDataRole.DisplayRole))
        self.dataChanged.emit(index, index, [role])
        return True

    def setStringList(self, strings: list[str]):
        super().setStringList(strings)
        self._set_mod_states()

    def data(self, index: QModelIndex, role: int = ...) -> Any:
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.CheckStateRole:
            return (
                Qt.CheckState.Checked
                if self.data(index, Qt.ItemDataRole.DisplayRole) in self._checked_items
                else Qt.CheckState.Unchecked
            )

        return super().data(index, role)

    def canDropMimeData(
        self,
        data: QMimeData | None,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if action == Qt.DropAction.MoveAction and (row != -1 or column != -1):
            return True
        return False


class UE4SSView(QListView):
    data_dropped = pyqtSignal()

    def __init__(self, parent: QWidget | None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.viewport().setAcceptDrops(True)

    def dropEvent(self, e: QDropEvent | None):
        super().dropEvent(e)
        self.data_dropped.emit()

    def dataChanged(self, topLeft, bottomRight, roles=...):
        super().dataChanged(topLeft, bottomRight, roles)
        self.repaint()


class UE4SSTabWidget(QWidget):
    def __init__(self, parent: QWidget | None, organizer: mobase.IOrganizer):
        super().__init__(parent)
        self._organizer = organizer
        self._view = UE4SSView(self)
        self._layout = QGridLayout(self)
        self._layout.addWidget(self._view)
        self._model = UE4SSListModel(self._view, organizer)
        self._view.setModel(self._model)
        self._model.dataChanged.connect(self.write_mod_list)
        self._view.data_dropped.connect(self.write_mod_list)
        self._parse_mod_files()

    def update_mod_files(self, state: dict[str, mobase.ModState]):
        for mod, state in state.items():
            tree = self._organizer.modList().getMod(mod).fileTree()
            ue4ss_files = tree.find("UE4SS")
            if not ue4ss_files:
                ue4ss_files = tree.find(
                    "Root/OblivionRemastered/Binaries/Win64/ue4ss/Mods"
                )
            if ue4ss_files:
                for entry in ue4ss_files:
                    if entry.isDir():
                        if entry.find("enabled.txt"):
                            enabled_txt: mobase.FileTreeEntry = entry.find(
                                "enabled.txt"
                            )
                            try:
                                os.remove(
                                    self._organizer.modList().getMod(mod).absolutePath()
                                    + "/"
                                    + enabled_txt.path("/")
                                )
                                self._organizer.modDataChanged(
                                    self._organizer.modList().getMod(mod)
                                )
                            except FileNotFoundError:
                                pass

        self._parse_mod_files()

    def _parse_mod_files(self):
        mod_list = set()
        for mod in self._organizer.modList().allMods():
            if (
                mobase.ModState(self._organizer.modList().state(mod))
                & mobase.ModState.ACTIVE
            ):
                tree = self._organizer.modList().getMod(mod).fileTree()
                ue4ss_files = tree.find("UE4SS")
                if not ue4ss_files:
                    ue4ss_files = tree.find(
                        "Root/OblivionRemastered/Binaries/Win64/ue4ss/Mods"
                    )
                if ue4ss_files:
                    for entry in ue4ss_files:
                        if entry.isDir():
                            if entry.find("scripts/main.lua"):
                                mod_list.add(entry.name())
                            if entry.find("enabled.txt"):
                                enabled_txt: mobase.FileTreeEntry = entry.find(
                                    "enabled.txt"
                                )
                                try:
                                    os.remove(
                                        self._organizer.modList()
                                        .getMod(mod)
                                        .absolutePath()
                                        + "/"
                                        + enabled_txt.path("/")
                                    )
                                    self._organizer.modDataChanged(
                                        self._organizer.modList().getMod(mod)
                                    )
                                except FileNotFoundError:
                                    pass

        game = self._organizer.managedGame()  # type: OblivionRemasteredGame
        if type(game) is OblivionRemasteredGame:
            if game.ue4ssDirectory().exists():
                for dir_info in game.ue4ssDirectory().entryInfoList(
                    QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot
                ):
                    if QFileInfo(
                        QDir(dir_info.absoluteFilePath()).absoluteFilePath(
                            "scripts/main.lua"
                        )
                    ).exists():
                        mod_list.add(dir_info.fileName())
                    if QFileInfo(
                        QDir(dir_info.absoluteFilePath()).absoluteFilePath(
                            "enabled.txt"
                        )
                    ).exists():
                        os.remove(dir_info.dir().absoluteFilePath("enabled.txt"))
        final_list = sorted(mod_list, key=cmp_to_key(self.sort_mods))
        self._model.setStringList(final_list)

    def write_mod_list(self):
        mod_list: list[dict] = []
        profile = QDir(self._organizer.profilePath())
        mods_txt = QFileInfo(profile.absoluteFilePath("mods.txt"))
        with open(mods_txt.absoluteFilePath(), "w") as txt_file:
            for i in range(self._model.rowCount()):
                item = self._model.index(i, 0)
                name = self._model.data(item, Qt.ItemDataRole.DisplayRole)
                active = (
                    True
                    if self._model.data(item, Qt.ItemDataRole.CheckStateRole)
                    == Qt.CheckState.Checked
                    else False
                )
                mod_list.append({"mod_name": name, "mod_enabled": active})
                txt_file.write(f"{name} : {1 if active else 0}\n")
        mods_json = QFileInfo(profile.absoluteFilePath("mods.json"))
        with open(mods_json.absoluteFilePath(), "w") as json_file:
            json_file.write(json.dumps(mod_list, indent=4))

    def sort_mods(self, mod_a: str, mod_b: str) -> int:
        profile = QDir(self._organizer.profilePath())
        mods_json = QFileInfo(profile.absoluteFilePath("mods.json"))
        mods_list = []
        if mods_json.exists() and mods_json.isFile():
            with open(mods_json.absoluteFilePath(), "r") as json_file:
                mods = json.load(json_file)
                for mod in mods:
                    if mod["mod_enabled"]:
                        mods_list.append(mod["mod_name"])
        index_a = -1
        if mod_a in mods_list:
            index_a = mods_list.index(mod_a)
        index_b = -1
        if mod_b in mods_list:
            index_b = mods_list.index(mod_b)
        if index_a != -1 and index_b != -1:
            return index_a - index_b
        if index_a != -1:
            return -1
        if index_b != -1:
            return 1
        if mod_a < mod_b:
            return -1
        return 1


class OblivionRemasteredModDataChecker(mobase.ModDataChecker):
    _dirs = ["Data", "Paks", "OBSE", "Movies", "UE4SS", "Root"]
    _data_dirs = [
        "meshes",
        "textures",
        "music",
        # "scripts",
        "fonts",
        "interface",
        "shaders",
        "strings",
        "materials",
    ]
    _data_extensions = [".esm", ".esp", ".bsa"]

    def __init__(self):
        super().__init__()

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        status = mobase.ModDataChecker.INVALID
        if filetree.find("ue4ss/UE4SS.dll") is not None:
            return mobase.ModDataChecker.FIXABLE
        elif (
            filetree.find("OblivionRemastered/Binaries/Win64/ue4ss/UE4SS.dll")
            is not None
        ):
            return mobase.ModDataChecker.FIXABLE
        for entry in filetree:
            name = entry.name().casefold()
            if entry.parent().parent() is None:
                if is_directory(entry):
                    if name in [dirname.lower() for dirname in self._dirs]:
                        status = mobase.ModDataChecker.VALID
                        break
                    elif name in [dirname.lower() for dirname in self._data_dirs]:
                        status = mobase.ModDataChecker.FIXABLE
                    else:
                        for sub_entry in entry:
                            if not is_directory(sub_entry):
                                sub_name = sub_entry.name().casefold()
                                if sub_name.endswith(".exe"):
                                    return mobase.ModDataChecker.INVALID
                                if sub_name.endswith((".pak", ".bk2")):
                                    status = mobase.ModDataChecker.FIXABLE
                                elif sub_name.endswith(tuple(self._data_extensions)):
                                    status = mobase.ModDataChecker.FIXABLE
                            else:
                                if name == "Paks":
                                    status = mobase.ModDataChecker.FIXABLE
                        new_status = self.dataLooksValid(entry)
                        if new_status != mobase.ModDataChecker.INVALID:
                            status = new_status
                        if status == mobase.ModDataChecker.VALID:
                            break
                else:
                    if name.endswith(".exe"):
                        return mobase.ModDataChecker.INVALID
                    if name.endswith(tuple(self._data_extensions + [".pak", ".bk2"])):
                        status = mobase.ModDataChecker.FIXABLE
            else:
                if is_directory(entry):
                    if name in [dir_name.lower() for dir_name in self._dirs]:
                        status = mobase.ModDataChecker.FIXABLE
                    if name in [dir_name.lower() for dir_name in self._data_dirs]:
                        status = mobase.ModDataChecker.FIXABLE
                    else:
                        new_status = self.dataLooksValid(entry)
                        if new_status != mobase.ModDataChecker.INVALID:
                            status = new_status
                else:
                    if name.endswith(".exe"):
                        return mobase.ModDataChecker.INVALID
                    if name.endswith(
                        tuple(self._data_extensions + [".pak", ".lua", ".bk2"])
                    ):
                        status = mobase.ModDataChecker.FIXABLE
                if status == mobase.ModDataChecker.VALID:
                    break
        return status

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        ue4ss_dll = filetree.find("ue4ss/UE4SS.dll")
        if ue4ss_dll is None:
            ue4ss_dll = filetree.find(
                "OblivionRemastered/Binaries/Win64/ue4ss/UE4SS.dll"
            )
        if ue4ss_dll is not None:
            entries = []
            for entry in ue4ss_dll.parent().parent():
                entries.append(entry)
            for entry in entries:
                filetree.move(
                    entry,
                    "Root/OblivionRemastered/Binaries/Win64/",
                    mobase.IFileTree.MERGE,
                )
        exe_dir = filetree.find(r"OblivionRemastered\Binaries\Win64")
        if exe_dir is not None:
            obse_dir = exe_dir.find("OBSE")
            if obse_dir:
                obse_main = self.get_dir(filetree, "OBSE")
                obse_main.merge(obse_dir, True)
                obse_dir.detach()
            ue4ss_mod_dir = exe_dir.find("ue4ss/Mods")
            if ue4ss_mod_dir:
                ue4ss_main = self.get_dir(filetree, "UE4SS")
                ue4ss_main.merge(ue4ss_mod_dir, True)
                ue4ss_mod_dir.detach()
            if len(exe_dir):
                root_exe_dir = self.get_dir(
                    filetree, "Root/OblivionRemastered/Binaries"
                )
                parent = exe_dir.parent()
                exe_dir.moveTo(root_exe_dir)
                self.detach_parents(parent)
            else:
                self.detach_parents(exe_dir)
        directories = []
        for entry in filetree:
            if entry is not None:
                if is_directory(entry):
                    directories.append(entry)
        for directory in directories:
            if directory.name().casefold() in [
                dirname.lower() for dirname in self._data_dirs
            ]:
                data_dir = self.get_dir(filetree, "Data")
                directory.moveTo(data_dir)
            elif directory.name().casefold() not in [
                dirname.lower() for dirname in self._dirs
            ]:
                filetree = self.parse_directory(filetree, directory)
        for entry in filetree:
            if entry is not None:
                if not is_directory(entry):
                    name = entry.name().casefold()
                    if name.endswith(".pak"):
                        paks_dir = self.get_dir(filetree, "Paks/~mods")
                        pak_files: list[mobase.FileTreeEntry] = []
                        for file in entry.parent():
                            if file is not None:
                                if not is_directory(file):
                                    if (
                                        file.name()
                                        .casefold()
                                        .endswith((".pak", ".ucas", ".utoc"))
                                    ):
                                        pak_files.append(file)
                        for pak_file in pak_files:
                            pak_file.moveTo(paks_dir)
                    elif name.endswith(".bk2"):
                        movies_dir = self.get_dir(filetree, "Movies/Modern")
                        movie_files: list[mobase.FileTreeEntry] = []
                        for file in entry.parent():
                            if file is not None:
                                if not is_directory(file):
                                    if file.name().casefold().endswith(".bk2"):
                                        movie_files.append(file)
                        for movie_file in movie_files:
                            movie_file.moveTo(movies_dir)
                    elif name.endswith(tuple(self._data_extensions)):
                        data_dir = self.get_dir(filetree, "Data")
                        data_files: list[mobase.FileTreeEntry] = []
                        for file in entry.parent():
                            data_files.append(file)
                        for data_file in data_files:
                            data_file.moveTo(data_dir)
        return filetree

    def parse_directory(
        self, main_filetree: mobase.IFileTree, next_dir: mobase.IFileTree
    ) -> mobase.IFileTree:
        directories = []
        for entry in next_dir:
            if entry is not None:
                if is_directory(entry):
                    directories.append(entry)
        for directory in directories:
            name = directory.name().casefold()
            stop = False
            for dir_name in self._dirs:
                if name == dir_name.lower():
                    main_dir = self.get_dir(main_filetree, dir_name)
                    if name == "ue4ss":
                        mod_dir = directory.find("Mods")
                        if mod_dir:
                            main_dir.merge(mod_dir)
                        else:
                            main_dir.merge(directory)
                    else:
                        main_dir.merge(directory)
                    self.detach_parents(directory)
                    stop = True
                    break
            if stop:
                continue
            if name in ["~mods", "logicmods"]:
                paks_dir = self.get_dir(main_filetree, "Paks")
                directory.moveTo(paks_dir)
                continue
            elif name in [dirname.lower() for dirname in self._data_dirs]:
                data_dir = self.get_dir(main_filetree, "Data")
                data_dir.merge(directory)
                self.detach_parents(directory)
                continue
            main_filetree = self.parse_directory(main_filetree, directory)
        for entry in next_dir:
            if not is_directory(entry):
                name = entry.name().casefold()
                if name.endswith(tuple(self._data_extensions)):
                    data_dir = self.get_dir(main_filetree, "Data")
                    data_dir.merge(next_dir)
                    self.detach_parents(next_dir)
                elif name.endswith(".pak"):
                    paks_dir = self.get_dir(main_filetree, "Paks")
                    if next_dir.name().casefold() == "paks":
                        paks_dir.merge(next_dir)
                        self.detach_parents(next_dir)
                        return main_filetree
                    elif next_dir.name().casefold() in ["~mods", "logicmods"]:
                        next_dir.moveTo(paks_dir)
                        return main_filetree
                    else:
                        parent = next_dir.parent()
                        main_filetree.move(
                            next_dir, "Paks/~mods/", mobase.IFileTree.MERGE
                        )
                        self.detach_parents(parent)
                        return main_filetree
                elif name.endswith(".lua"):
                    if next_dir.parent() and next_dir.parent() != main_filetree:
                        if main_filetree.find("UE4SS") is None:
                            main_filetree.addDirectory("UE4SS")
                        parent = next_dir.parent().parent()
                        main_filetree.move(
                            next_dir.parent(),
                            "UE4SS/",
                            mobase.IFileTree.MERGE,
                        )
                        if parent is not None:
                            self.detach_parents(parent)
                        return main_filetree
                elif name.endswith(".bk2"):
                    movies_dir = self.get_dir(main_filetree, "Movies/Modern")
                    movies_dir.merge(next_dir)
                    self.detach_parents(next_dir)

        return main_filetree

    def detach_parents(self, directory: mobase.IFileTree) -> None:
        if directory.parent() is not None and len(directory.parent()) == 1:
            parent = (
                directory.parent()
                if directory.parent().parent() is not None
                else directory
            )
            while parent.parent().parent() is not None and len(parent.parent()) == 1:
                parent = parent.parent()
            parent.detach()
        else:
            if len(directory) == 1:
                directory.detach()

    def get_dir(self, filetree: mobase.IFileTree, directory: str) -> mobase.IFileTree:
        tree_dir = filetree.find(directory)
        if tree_dir is None:
            tree_dir = filetree.addDirectory(directory)
        return tree_dir


class OblivionRemasteredDataContent(mobase.ModDataContent):
    OR_CONTENTS: tuple[Content, str, str, bool | None] = [
        (Content.PLUGIN, "Plugins (ESM/ESP)", ":/MO/gui/content/plugin"),
        (Content.BSA, "Bethesda Archive", ":/MO/gui/content/bsa"),
        (Content.PAK, "Paks", ":/MO/gui/content/geometries"),
        (Content.OBSE, "Script Extender Plugin", ":/MO/gui/content/skse"),
        (Content.OBSE_FILES, "Script Extender Files", "", True),
        (Content.MOVIE, "Movies", ":/MO/gui/content/media"),
        (Content.UE4SS, "UE4SS Mods", ":/MO/gui/content/script"),
        (Content.MAGIC_LOADER, "Magic Loader Mod", ":/MO/gui/content/inifile"),
    ]

    def getAllContents(self) -> list[mobase.ModDataContent.Content]:
        return [mobase.ModDataContent.Content(*content) for content in self.OR_CONTENTS]

    def getContentsFor(self, filetree: mobase.IFileTree) -> list[int]:
        contents: set[int] = set()

        for entry in filetree:
            if is_directory(entry):
                match entry.name().casefold():
                    case "data":
                        for data_entry in entry:
                            if not is_directory(data_entry):
                                match data_entry.suffix().casefold():
                                    case "esm" | "esp":
                                        contents.add(Content.PLUGIN)
                                    case "bsa":
                                        contents.add(Content.BSA)
                                    case _:
                                        pass
                            else:
                                match data_entry.name().casefold():
                                    case "magicloader":
                                        contents.add(Content.MAGIC_LOADER)
                    case "obse":
                        contents.add(Content.OBSE_FILES)
                        plugins_dir = entry.find("Plugins")
                        if plugins_dir:
                            for plugin_entry in plugins_dir:
                                if plugin_entry.suffix().casefold() == "dll":
                                    contents.add(Content.OBSE)
                                    break
                    case "paks":
                        contents.add(Content.PAK)
                        for paks_entry in entry:
                            if is_directory(paks_entry):
                                if paks_entry.name().casefold() == "~mods":
                                    if paks_entry.find("MagicLoader"):
                                        contents.add(Content.MAGIC_LOADER)
                                if paks_entry.name().casefold() == "logicmods":
                                    contents.add(Content.UE4SS)
                    case "movies":
                        contents.add(Content.MOVIE)
                    case "ue4ss":
                        contents.add(Content.UE4SS)

        return list(contents)


class OblivionRemasteredGamePlugins(mobase.GamePlugins):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self._last_read = QDateTime().currentDateTime()
        self._organizer = organizer
        # What are these for?
        self._plugin_blacklist = ["TamrielLevelledRegion.esp", "AltarGymNavigation.esp"]

    def writePluginLists(self, plugin_list: mobase.IPluginList) -> None:
        if not self._last_read.isValid():
            return
        self.writePluginList(
            plugin_list, self._organizer.profile().absolutePath() + "/plugins.txt"
        )
        self.writeLoadOrderList(
            plugin_list, self._organizer.profile().absolutePath() + "/loadorder.txt"
        )
        self._last_read = QDateTime.currentDateTime()

    def readPluginLists(self, plugin_list: mobase.IPluginList) -> None:
        load_order_path = self._organizer.profile().absolutePath() + "/loadorder.txt"
        load_order = self.readLoadOrderList(plugin_list, load_order_path)
        plugin_list.setLoadOrder(load_order)
        self.readPluginList(plugin_list)
        self._last_read = QDateTime.currentDateTime()

    def getLoadOrder(self) -> Sequence[str]:
        load_order_path = self._organizer.profile().absolutePath() + "/loadorder.txt"
        plugins_path = self._organizer.profile().absolutePath() + "/plugins.txt"

        load_order_is_new = (
            not self._last_read.isValid()
            or not QFileInfo(load_order_path).exists()
            or QFileInfo(load_order_path).lastModified() > self._last_read
        )
        plugins_is_new = (
            not self._last_read.isValid()
            or QFileInfo(plugins_path).lastModified() > self._last_read
        )

        if load_order_is_new or not plugins_is_new:
            return self.readLoadOrderList(self._organizer.pluginList(), load_order_path)
        else:
            return self.readPluginList(self._organizer.pluginList())

    def writePluginList(self, plugin_list: mobase.IPluginList, filePath: str):
        self.writeList(plugin_list, filePath, False)

    def writeLoadOrderList(self, plugin_list: mobase.IPluginList, filePath: str):
        self.writeList(plugin_list, filePath, True)

    def writeList(
        self, plugin_list: mobase.IPluginList, filePath: str, load_order: bool
    ):
        plugins_file = open(filePath, "w")
        encoder = (
            QStringEncoder(QStringConverter.Encoding.Utf8)
            if load_order
            else QStringEncoder(QStringConverter.Encoding.System)
        )
        plugins_text = "# This file was automatically generated by Mod Organizer.\n"
        invalid_filenames = False
        written_count = 0
        plugins = plugin_list.pluginNames()
        plugins_sorted = sorted(
            plugins,
            key=cmp_to_key(
                lambda lhs, rhs: plugin_list.priority(lhs) - plugin_list.priority(rhs)
            ),
        )
        for plugin_name in plugins_sorted:
            if (
                load_order
                or plugin_list.state(plugin_name) == mobase.PluginState.ACTIVE
            ):
                result = encoder.encode(plugin_name)
                if encoder.hasError():
                    invalid_filenames = True
                    qCritical("invalid plugin name %s", plugin_name)
                plugins_text += result.data().decode() + "\n"
                written_count += 1

        if invalid_filenames:
            qCritical(
                QCoreApplication.translate(
                    "MainWindow",
                    "Some of your plugins have invalid names! These "
                    + "plugins can not be loaded by the game. Please see "
                    + "mo_interface.log for a list of affected plugins "
                    + "and rename them.",
                )
            )

        if written_count == 0:
            qWarning(
                "plugin list would be empty, this is almost certainly wrong. Not saving."
            )
        else:
            plugins_file.write(plugins_text)
        plugins_file.close()

    def readLoadOrderList(
        self, plugin_list: mobase.IPluginList, file_path: str
    ) -> list[str]:
        plugin_names = [
            plugin for plugin in self._organizer.managedGame().primaryPlugins()
        ]
        plugin_lookup = set()
        for name in plugin_names:
            if name.lower() not in plugin_lookup:
                plugin_lookup.add(name.lower())

        try:
            with open(file_path) as file:
                for line in file:
                    if line.startswith("#"):
                        continue
                    plugin_file = line.rstrip("\n")
                    if plugin_file.lower() not in plugin_lookup:
                        plugin_lookup.add(plugin_file.lower())
                        plugin_names.append(plugin_file)
        except FileNotFoundError:
            return self.readPluginList(plugin_list)

        return plugin_names

    def readPluginList(self, plugin_list: mobase.IPluginList) -> list[str]:
        plugins = [plugin for plugin in plugin_list.pluginNames()]
        sorted_plugins = []
        primary = [plugin for plugin in self._organizer.managedGame().primaryPlugins()]
        primary_lower = [plugin.lower() for plugin in primary]
        for plugin_name in primary:
            if plugin_list.state(plugin_name) != mobase.PluginState.MISSING:
                plugin_list.setState(plugin_name, mobase.PluginState.ACTIVE)
            sorted_plugins.append(plugin_name)
        plugin_remove = [
            plugin for plugin in plugins if plugin.lower() in primary_lower
        ]
        for plugin in plugin_remove:
            plugins.remove(plugin)

        plugins_txt_exists = True
        file_path = self._organizer.profile().absolutePath() + "/plugins.txt"
        file = QFile(file_path)
        if not file.open(QFile.OpenModeFlag.ReadOnly):
            plugins_txt_exists = False
        if file.size() == 0:
            plugins_txt_exists = False
        if plugins_txt_exists:
            while not file.atEnd():
                line = file.readLine()
                file_plugin_name = QByteArray()
                if line.size() > 0 and line.at(0).decode() != "#":
                    encoder = QStringEncoder(QStringEncoder.Encoding.System)
                    file_plugin_name = encoder.encode(line.trimmed().data().decode())
                if file_plugin_name.size() > 0:
                    if file_plugin_name.data().decode().lower() in [
                        plugin.lower() for plugin in plugins
                    ]:
                        plugin_list.setState(
                            file_plugin_name.data().decode(), mobase.PluginState.ACTIVE
                        )
                        sorted_plugins.append(file_plugin_name.data().decode())
                        plugins.remove(file_plugin_name.data().decode())

            file.close()

            for plugin_name in plugins:
                plugin_list.setState(plugin_name, mobase.PluginState.INACTIVE)
        else:
            for plugin_name in plugins:
                plugin_list.setState(plugin_name, mobase.PluginState.INACTIVE)

        return sorted_plugins + plugins

    def lightPluginsAreSupported(self) -> bool:
        return False

    def mediumPluginsAreSupported(self) -> bool:
        return False

    def blueprintPluginsAreSupported(self) -> bool:
        return False


class OblivionRemasteredScriptExtender(mobase.ScriptExtender):
    def __init__(self, game: mobase.IPluginGame):
        super().__init__()
        self._game = game

    def binaryName(self):
        return "obse64_loader.exe"

    def loaderName(self) -> str:
        return self.binaryName()

    def loaderPath(self) -> str:
        return (
            self._game.gameDirectory().absolutePath()
            + "\\OblivionRemastered\\Binaries\\Win64\\"
            + self.loaderName()
        )

    def pluginPath(self) -> str:
        return "OBSE/Plugins"

    def savegameExtension(self) -> str:
        return ""

    def isInstalled(self) -> bool:
        return os.path.exists(self.loaderPath())

    def getExtenderVersion(self) -> str:
        return mobase.getFileVersion(self.loaderPath())

    def getArch(self) -> int:
        return 0x8664 if self.isInstalled() else 0x0


class OblivionRemasteredGame(
    BasicGame, mobase.IPluginFileMapper, mobase.IPluginDiagnose
):
    Name = "Oblivion Remastered Support Plugin"
    Author = "Silarn"
    Version = "0.1.0-b.1"
    Description = "TES IV: Oblivion Remastered; an unholy hybrid of Gamebryo and Unreal"

    GameName = "Oblivion Remastered"
    GameShortName = "oblivionremastered"
    GameNexusId = 7587
    GameSteamId = 2623190
    GameBinary = "OblivionRemastered.exe"
    GameDataPath = r"%GAME_PATH%\OblivionRemastered\Content\Dev\ObvData\Data"
    GameDocumentsDirectory = r"%GAME_PATH%\OblivionRemastered\Content\Dev\ObvData"
    UserHome = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.HomeLocation
    )
    MyDocumentsDirectory = rf"{UserHome}\Documents\My Games\{GameName}"
    GameSavesDirectory = rf"{MyDocumentsDirectory}\Saved\SaveGames"
    GameSaveExtension = "sav"

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)
        mobase.IPluginDiagnose.__init__(self)
        self._main_window = None
        self._ue4ss_tab = None

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(BasicGameSaveGameInfo())
        self._register_feature(OblivionRemasteredGamePlugins(self._organizer))
        self._register_feature(OblivionRemasteredModDataChecker())
        self._register_feature(OblivionRemasteredScriptExtender(self))
        self._register_feature(OblivionRemasteredDataContent())

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
        self._organizer.modList().onModStateChanged(self._ue4ss_tab.update_mod_files)

        plugin_tab = tab_widget.findChild(QWidget, "espTab")
        tab_index = tab_widget.indexOf(plugin_tab) + 1
        if not tab_widget.isTabVisible(tab_widget.indexOf(plugin_tab)):
            tab_index += 1
        tab_widget.insertTab(tab_index, self._ue4ss_tab, "UE4SS Mods")

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Oblivion Remastered",
                QFileInfo(
                    QDir(
                        self.gameDirectory().absoluteFilePath(
                            "OblivionRemastered/Binaries/Win64"
                        )
                    ),
                    "OblivionRemastered-Win64-Shipping.exe",
                ),
            ),
            mobase.ExecutableInfo(
                "OBSE64",
                QFileInfo(
                    self._organizer.gameFeatures()
                    .gameFeature(mobase.ScriptExtender)
                    .loaderPath()
                ),
            ),
            mobase.ExecutableInfo("LOOT", QFileInfo(str(getLootPath()))).withArgument(
                '--game="Oblivion Remastered"'
            ),
        ]

    def primaryPlugins(self) -> list[str]:
        return [
            "Oblivion.esm",
            "DLCBattlehornCastle.esp",
            "DLCFrostcrag.esp",
            "DLCHorseArmor.esp",
            "DLCMehrunesRazor.esp",
            "DLCOrrery.esp",
            "DLCShiveringIsles.esp",
            "DLCSpellTomes.esp",
            "DLCThievesDen.esp",
            "DLCVileLair.esp",
            "Knights.esp",
            "AltarESPMain.esp",
            "AltarDeluxe.esp",
            "AltarESPLocal.esp",
        ]

    def modDataDirectory(self) -> str:
        return "Data"

    def moviesDirectory(self) -> QDir:
        return QDir(
            self.gameDirectory().absolutePath() + "/OblivionRemastered/Content/Movies"
        )

    def paksDirectory(self) -> QDir:
        return QDir(
            self.gameDirectory().absolutePath() + "/OblivionRemastered/Content/Paks"
        )

    def exeDirectory(self) -> QDir:
        return QDir(
            self.gameDirectory().absolutePath() + "/OblivionRemastered/Binaries/Win64"
        )

    def obseDirectory(self) -> QDir:
        return QDir(self.exeDirectory().absolutePath() + "/OBSE")

    def ue4ssDirectory(self) -> QDir:
        return QDir(self.exeDirectory().absolutePath() + "/ue4ss/Mods")

    def loadOrderMechanism(self) -> mobase.LoadOrderMechanism:
        return mobase.LoadOrderMechanism.PLUGINS_TXT

    def sortMechanism(self) -> mobase.SortMechanism:
        return mobase.SortMechanism.LOOT

    def initializeProfile(
        self, directory: QDir, settings: mobase.ProfileSetting
    ) -> None:
        if settings & mobase.ProfileSetting.CONFIGURATION:
            game_ini_file = self.gameDirectory().absoluteFilePath(
                r"OblivionRemastered\Content\Dev\ObvData\Oblivion.ini"
            )
            game_default_ini = self.gameDirectory().absoluteFilePath(
                r"OblivionRemastered\Content\Dev\ObvData\Oblivion_default.ini"
            )
            profile_ini = directory.absoluteFilePath(
                QFileInfo("Oblivion.ini").fileName()
            )
            if not os.path.exists(profile_ini):
                try:
                    shutil.copyfile(
                        game_ini_file,
                        profile_ini,
                    )
                except FileNotFoundError:
                    if os.path.exists(game_ini_file):
                        shutil.copyfile(
                            game_default_ini,
                            profile_ini,
                        )
                    else:
                        Path(profile_ini).touch()
        self.write_default_mods(directory)
        if (
            self._organizer.managedGame()
            and self._organizer.managedGame().gameName() == self.gameName()
        ):
            if not self.paksDirectory().exists():
                os.makedirs(self.paksDirectory().absolutePath())
            if not self.obseDirectory().exists():
                os.makedirs(self.obseDirectory().absolutePath())
            if not self.ue4ssDirectory().exists():
                os.makedirs(self.ue4ssDirectory().absolutePath())

    def write_default_mods(self, profile: QDir):
        ue4ss_mods_txt = QFileInfo(profile.absoluteFilePath("mods.txt"))
        ue4ss_mods_json = QFileInfo(profile.absoluteFilePath("mods.json"))
        if not ue4ss_mods_txt.exists():
            with open(ue4ss_mods_txt.absoluteFilePath(), "w") as mods_txt:
                for mod in DEFAULT_UE4SS_MODS:
                    mods_txt.write(f"{mod} : 1\n")
        if not ue4ss_mods_json.exists():
            mods_data = []
            for mod in DEFAULT_UE4SS_MODS:
                mods_data.append({"mod_name": mod, "mod_enabled": True})
            with open(ue4ss_mods_json.absoluteFilePath(), "w") as mods_json:
                mods_json.write(json.dumps(mods_data, indent=4))

    def iniFiles(self) -> list[str]:
        return ["Oblivion.ini"]

    def mappings(self) -> list[mobase.Mapping]:
        mappings: list[mobase.Mapping] = []
        for profile_file in ["plugins.txt", "loadorder.txt"]:
            mappings.append(
                mobase.Mapping(
                    self._organizer.profilePath() + "/" + profile_file,
                    self.dataDirectory().absolutePath() + "/" + profile_file,
                    False,
                )
            )
        for profile_file in ["mods.txt", "mods.json"]:
            mappings.append(
                mobase.Mapping(
                    self._organizer.profilePath() + "/" + profile_file,
                    self.ue4ssDirectory().absolutePath() + "/" + profile_file,
                    False,
                )
            )
        return mappings

    def getModMappings(self) -> dict[str, list[str]]:
        return {
            "Data": [self.dataDirectory().absolutePath()],
            "Paks": [self.paksDirectory().absolutePath()],
            "OBSE": [self.obseDirectory().absolutePath()],
            "Movies": [self.moviesDirectory().absolutePath()],
            "UE4SS": [self.ue4ssDirectory().absolutePath()],
        }

    def activeProblems(self) -> list[int]:
        if self._organizer.managedGame() == self:
            problems: set[Problems] = set()
            ue4ss_loader = QFileInfo(self.exeDirectory().absoluteFilePath("dwmapi.dll"))
            if ue4ss_loader.exists():
                problems.add(Problems.UE4SS_LOADER)
            return list(problems)
        return []

    def fullDescription(self, key: int) -> str:
        match key:
            case Problems.UE4SS_LOADER:
                return (
                    "The UE4SS loader DLL is present (dwmapi.dll). This will not function out-of-the box with MO2's virtual filesystem.\n\n"
                    + "In order to resolve this, the DLL should be renamed (ex. 'ue4ss_loader.dll') and set to force load with the game exe.\n\n"
                    + "Do this for any executable which runs the game, such as the OBSE64 loader."
                )
        return ""

    def hasGuidedFix(self, key: int) -> bool:
        match key:
            case Problems.UE4SS_LOADER:
                return True
        return False

    def shortDescription(self, key: int) -> str:
        match key:
            case Problems.UE4SS_LOADER:
                return "The UE4SS loader DLL is present (dwmapi.dll)."
        return ""

    def startGuidedFix(self, key: int) -> None:
        match key:
            case Problems.UE4SS_LOADER:
                os.rename(
                    self.exeDirectory().absoluteFilePath("dwmapi.dll"),
                    self.exeDirectory().absoluteFilePath("ue4ss_loader.dll"),
                )
        pass
