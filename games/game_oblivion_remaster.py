import os.path
import shutil
import winreg
from functools import cmp_to_key
from pathlib import Path
from typing import Sequence

import PyQt6.QtCore
from PyQt6.QtCore import (
    QByteArray,
    QCoreApplication,
    QDateTime,
    QDir,
    QFile,
    QFileInfo,
    QStandardPaths,
    QStringConverter,
    QStringEncoder,
    qCritical,
)

import mobase

from ..basic_features import BasicGameSaveGameInfo
from ..basic_features.utils import is_directory
from ..basic_game import BasicGame


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


class OblivionRemasteredModDataChecker(mobase.ModDataChecker):
    _dirs = ["Data", "Paks", "OBSE", "Movies", "Root"]
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
    _extensions = [".esm", ".esp", ".bsa", ".ini", ".dll"]

    def __init__(self):
        super().__init__()

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        status = mobase.ModDataChecker.INVALID
        for entry in filetree:
            name = entry.name().casefold()
            if entry.parent().parent() is None:
                if is_directory(entry):
                    if name in [dirname.lower() for dirname in self._dirs]:
                        if name in ["obse", "root", "movies"]:
                            status = mobase.ModDataChecker.VALID
                            break
                        for sub_entry in entry:
                            if not is_directory(sub_entry):
                                sub_name = sub_entry.name().casefold()
                                if name == "paks":
                                    if sub_name.endswith(".pak"):
                                        status = mobase.ModDataChecker.VALID
                                        break
                                if name == "data":
                                    if sub_name.endswith(tuple(self._extensions)):
                                        status = mobase.ModDataChecker.VALID
                                        break
                            else:
                                if name == "paks":
                                    for paks_entry in sub_entry:
                                        if not is_directory(paks_entry):
                                            paks_name = paks_entry.name().casefold()
                                            if paks_name.endswith(".pak"):
                                                status = mobase.ModDataChecker.VALID
                                                break
                        if status == mobase.ModDataChecker.VALID:
                            break
                    else:
                        for sub_entry in entry:
                            if not is_directory(sub_entry):
                                sub_name = sub_entry.name().casefold()
                                if sub_name.endswith((".pak", ".lua", ".bk2")):
                                    status = mobase.ModDataChecker.FIXABLE
                                elif sub_name.endswith(tuple(self._extensions)):
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
                    if name.endswith(
                        tuple(self._extensions + [".pak", ".lua", ".bk2"])
                    ):
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
                    if name.endswith(
                        tuple(self._extensions + [".pak", ".lua", ".bk2"])
                    ):
                        status = mobase.ModDataChecker.FIXABLE
                if status == mobase.ModDataChecker.VALID:
                    break
        return status

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        for entry in filetree:
            if entry is not None:
                if is_directory(entry):
                    if entry.name().casefold() in [
                        dirname.lower() for dirname in self._data_dirs
                    ]:
                        data_dir = filetree.find("Data")
                        if data_dir is None:
                            data_dir = filetree.addDirectory("Data")
                        entry.moveTo(data_dir)
                    elif entry.name().casefold() not in [
                        dirname.lower() for dirname in self._dirs
                    ]:
                        filetree = self.parse_directory(filetree, entry)
                else:
                    name = entry.name().casefold()
                    if name.endswith(".pak"):
                        paks_dir = filetree.find("Paks")
                        if paks_dir is None:
                            paks_dir = filetree.addDirectory("Paks")
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
                        movies_dir = filetree.find("Movies/Modern")
                        if movies_dir is None:
                            movies_dir = filetree.addDirectory("Movies/Modern")
                        movie_files: list[mobase.FileTreeEntry] = []
                        for file in entry.parent():
                            if file is not None:
                                if not is_directory(file):
                                    if file.name().casefold().endswith(".bk2"):
                                        movie_files.append(file)
                        for movie_file in movie_files:
                            movie_file.moveTo(movies_dir)
                    elif name.endswith(tuple(self._extensions)):
                        data_dir = filetree.find("Data")
                        if data_dir is None:
                            data_dir = filetree.addDirectory("Data")
                        data_files: list[mobase.FileTreeEntry] = []
                        for file in entry.parent():
                            data_files.append(file)
                        for data_file in data_files:
                            data_file.moveTo(data_dir)
        return filetree

    def parse_directory(
        self, main_filetree: mobase.IFileTree, next_dir: mobase.IFileTree
    ) -> mobase.IFileTree:
        for entry in next_dir:
            name = entry.name().casefold()
            if is_directory(entry):
                for dir_name in self._dirs:
                    if name == dir_name.lower():
                        if name == "ue4ss":
                            ue4ss_mods = next_dir.find("Mods")
                            if ue4ss_mods:
                                if main_filetree.find("UE4SS") is None:
                                    main_filetree.addDirectory("UE4SS")
                                main_filetree.find("UE4SS").merge(ue4ss_mods)
                            else:
                                main_filetree.move(next_dir, "")
                            self.detach_parents(next_dir)
                            continue
                        elif name == "paks":
                            if entry.find("~mods"):
                                main_filetree = self.parse_directory(
                                    main_filetree, entry
                                )
                                continue
                        main_dir = main_filetree.find(dir_name)
                        if main_dir is None:
                            main_dir = main_filetree.addDirectory(dir_name)
                        main_dir.merge(entry)
                        self.detach_parents(entry)
                if name == "~mods":
                    paks_dir = main_filetree.find("Paks")
                    if paks_dir is None:
                        paks_dir = main_filetree.addDirectory("Paks")
                    paks_dir.merge(entry)
                    self.detach_parents(entry)
                    continue
                elif name in [dirname.lower() for dirname in self._data_dirs]:
                    data_dir = main_filetree.find("Data")
                    if data_dir is None:
                        data_dir = main_filetree.addDirectory("Data")
                    data_dir.merge(entry)
                    self.detach_parents(entry)
                    continue
                main_filetree = self.parse_directory(main_filetree, entry)
            else:
                if name.endswith(tuple(self._extensions)):
                    data_dir = main_filetree.find("Data")
                    if data_dir is None:
                        data_dir = main_filetree.addDirectory("Data")
                    data_dir.merge(next_dir)
                    self.detach_parents(next_dir)
                elif name.endswith(".pak"):
                    paks_dir = main_filetree.find("Paks")
                    if paks_dir is None:
                        paks_dir = main_filetree.addDirectory("Paks")
                    if next_dir.name().casefold() == "paks":
                        paks_dir.merge(next_dir)
                        self.detach_parents(next_dir)
                        return main_filetree
                    else:
                        main_filetree.move(next_dir, "Paks/")
                        return main_filetree
                elif name.endswith(".lua"):
                    if next_dir.parent() and next_dir.parent() != main_filetree:
                        if (
                            main_filetree.find(
                                "Root/OblivionRemastered/Binaries/Win64/ue4ss/Mods"
                            )
                            is None
                        ):
                            main_filetree.addDirectory(
                                "Root/OblivionRemastered/Binaries/Win64/ue4ss/Mods"
                            )
                        main_filetree.move(
                            next_dir.parent(),
                            "Root/OblivionRemastered/Binaries/Win64/ue4ss/Mods/",
                        )
                        self.detach_parents(main_filetree)
                        return main_filetree
                elif name.endswith(".bk2"):
                    movies_dir = main_filetree.find("Movies/Modern")
                    if movies_dir is None:
                        movies_dir = main_filetree.addDirectory("Movies/Modern")
                    movies_dir.merge(next_dir)
                    self.detach_parents(next_dir)

        return main_filetree

    def detach_parents(self, directory: mobase.IFileTree) -> None:
        if directory.parent() is not None:
            parent = (
                directory.parent()
                if directory.parent().parent() is not None
                else directory
            )
            while parent.parent().parent() is not None:
                parent = parent.parent()
            parent.detach()
        else:
            directory.detach()


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
            PyQt6.QtCore.qCritical(
                QCoreApplication.translate(
                    "MainWindow",
                    "Some of your plugins have invalid names! These "
                    + "plugins can not be loaded by the game. Please see "
                    + "mo_interface.log for a list of affected plugins "
                    + "and rename them.",
                )
            )

        if written_count == 0:
            PyQt6.QtCore.qWarning(
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


class OblivionRemasteredGame(BasicGame, mobase.IPluginFileMapper):
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

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(BasicGameSaveGameInfo())
        self._register_feature(OblivionRemasteredGamePlugins(self._organizer))
        self._register_feature(OblivionRemasteredModDataChecker())
        self._register_feature(OblivionRemasteredScriptExtender(self))
        return True

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Oblivion Remastered",
                QFileInfo(
                    self.gameDirectory(),
                    self.binaryName(),
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
            self.gameDirectory().absolutePath()
            + "/OblivionRemastered/Content/Paks/~mods"
        )

    def obseDirectory(self) -> QDir:
        return QDir(
            self.gameDirectory().absolutePath()
            + "/OblivionRemastered/Binaries/Win64/OBSE"
        )

    def ue4ssDirectory(self) -> QDir:
        return QDir(
            self.gameDirectory().absolutePath()
            + "/OblivionRemastered/Binaries/Win64/ue4ss/Mods"
        )

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
        return mappings

    def getModMappings(self) -> dict[str, list[str]]:
        return {
            "Data": [self.dataDirectory().absolutePath()],
            "Paks": [self.paksDirectory().absolutePath()],
            "OBSE": [self.obseDirectory().absolutePath()],
            "Movies": [self.moviesDirectory().absolutePath()],
        }
