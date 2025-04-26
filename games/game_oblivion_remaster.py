import os.path
from functools import cmp_to_key
from pathlib import Path
from typing import Dict, Sequence

import PyQt6.QtCore
import mobase
from PyQt6.QtCore import QByteArray, QDir, QFileInfo, QFile, QDateTime, QCoreApplication, QStandardPaths, \
    QStringEncoder, QStringConverter, qCritical, qDebug

from ..basic_features import BasicLocalSavegames, BasicGameSaveGameInfo, BasicModDataChecker, GlobPatterns
from ..basic_features.utils import is_directory
from ..basic_game import BasicGame

class OblivionRemasteredModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()

    def dataLooksValid(self, filetree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        status = mobase.ModDataChecker.INVALID
        dirs = [
            'meshes',
            'textures',
            'music',
            'scripts',
            'fonts',
            'interface',
            'shaders',
            'strings',
            'materials'
        ]
        extensions = [
            '.esm',
            '.esp',
            '.bsa',
            '.ini'
        ]
        if filetree.parent() is None:
            paks = filetree.find(r'OblivionRemastered\Content\Paks\~mods', mobase.FileTreeEntry.FileTypes.DIRECTORY)
            if paks is not None:
                return mobase.ModDataChecker.FIXABLE
            data = filetree.find(r'OblivionRemastered\Content\Dev\ObvData\Data', mobase.FileTreeEntry.FileTypes.DIRECTORY)
            if data is not None:
                return mobase.ModDataChecker.FIXABLE
        for entry in filetree:
            name = entry.name().casefold()

            if entry.parent().parent() is None:
                if is_directory(entry):
                    if name in dirs:
                        status = mobase.ModDataChecker.VALID
                        break
                    else:
                        for sub_entry in entry:
                            if not is_directory(sub_entry):
                                sub_name = sub_entry.name().casefold()
                                if sub_name.endswith('.pak'):
                                    status = mobase.ModDataChecker.VALID
                                    break
                                elif sub_name.endswith(tuple(extensions)):
                                    status = mobase.ModDataChecker.FIXABLE
                            else:
                                new_status = self.dataLooksValid(entry)
                                if new_status != mobase.ModDataChecker.INVALID:
                                    status = new_status
                        if status == mobase.ModDataChecker.VALID:
                            break
                else:
                    if name.endswith(tuple(extensions + ['.pak'])):
                        status = mobase.ModDataChecker.VALID
                        break

            else:
                if is_directory(entry):
                    new_status = self.dataLooksValid(entry)
                    if new_status != mobase.ModDataChecker.INVALID:
                        status = new_status
                else:
                    if name.endswith(tuple(extensions + ['.pak'])):
                        status = mobase.ModDataChecker.FIXABLE

        return status

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        paks = filetree.find(r'OblivionRemastered\Content\Paks\~mods', mobase.FileTreeEntry.FileTypes.DIRECTORY)
        if paks is not None:
            filetree.merge(paks)
            filetree.find('OblivionRemastered').detach()
        data = filetree.find(r'OblivionRemastered\Content\Dev\ObvData\Data', mobase.FileTreeEntry.FileTypes.DIRECTORY)
        if data is not None:
            filetree.merge(data)
            filetree.find('OblivionRemastered').detach()
        for entry in filetree:
            if is_directory(entry):
                filetree = self.parse_directory(filetree, entry)

        return filetree

    def parse_directory(self, main_filetree: mobase.IFileTree, next_dir: mobase.IFileTree) -> mobase.IFileTree:
        extensions = [
            '.esm',
            '.esp',
            '.bsa',
            '.ini'
        ]
        for entry in next_dir:
            name = entry.name().casefold()
            if is_directory(entry):
                self.parse_directory(main_filetree, entry)
            else:
                if name.endswith(tuple(extensions)):
                    main_filetree.merge(next_dir)
                    next_dir.detach()
                elif name.endswith('.pak'):
                    main_filetree.move(next_dir, '/')

        return main_filetree


class OblivionRemasteredGamePlugins(mobase.GamePlugins):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self._last_read = QDateTime().currentDateTime()
        self._organizer = organizer
        # What are these for?
        self._plugin_blacklist = ['TamrielLevelledRegion.esp', 'AltarGymNavigation.esp']

    def writePluginLists(self, plugin_list: mobase.IPluginList) -> None:
        if not self._last_read.isValid():
            return
        self.writePluginList(plugin_list, self._organizer.profile().absolutePath() + "/plugins.txt")
        self.writeLoadOrderList(plugin_list, self._organizer.profile().absolutePath() + "/loadorder.txt")
        self._last_read = QDateTime.currentDateTime()

    def readPluginLists(self, plugin_list: mobase.IPluginList) -> None:
        load_order_path = self._organizer.profile().absolutePath() + "/loadorder.txt"
        load_order = self.readLoadOrderList(plugin_list, load_order_path)
        plugin_list.setLoadOrder(load_order)
        self.readPluginList(plugin_list)
        self._last_read = QDateTime.currentDateTime()

    def getLoadOrder(self) -> Sequence[str]:
        load_order_path = self._organizer.profile().absolutePath() + "/loadorder.txt"
        plugins_path   = self._organizer.profile().absolutePath() + "/plugins.txt"

        load_order_is_new = (not self._last_read.isValid() or not QFileInfo(load_order_path).exists()
                          or QFileInfo(load_order_path).lastModified() > self._last_read)
        plugins_is_new = not self._last_read.isValid() or QFileInfo(plugins_path).lastModified() > self._last_read

        if load_order_is_new or not plugins_is_new:
            return self.readLoadOrderList(self._organizer.pluginList(), load_order_path)
        else:
            return self.readPluginList(self._organizer.pluginList())

    def writePluginList(self, plugin_list: mobase.IPluginList, filePath: str):
        self.writeList(plugin_list, filePath, False)

    def writeLoadOrderList(self, plugin_list: mobase.IPluginList, filePath: str):
        self.writeList(plugin_list, filePath, True)

    def writeList(self, plugin_list: mobase.IPluginList, filePath: str, load_order: bool):
        plugins_file = open(filePath, 'w')
        encoder = QStringEncoder(QStringConverter.Encoding.Utf8) if load_order else QStringEncoder(QStringConverter.Encoding.System)
        plugins_text = '# This file was automatically generated by Mod Organizer.\n'
        invalid_filenames = False
        written_count = 0
        plugins = plugin_list.pluginNames()
        plugins_sorted = sorted(plugins, key=cmp_to_key(lambda lhs, rhs: plugin_list.priority(lhs) - plugin_list.priority(rhs)))
        for plugin_name in plugins_sorted:
            if load_order or plugin_list.state(plugin_name) == mobase.PluginState.ACTIVE:
                result = encoder.encode(plugin_name)
                if encoder.hasError():
                    invalid_filenames = True
                    qCritical('invalid plugin name %s', plugin_name)
                plugins_text += result.data().decode() + '\n'
                written_count += 1

        if invalid_filenames:
            PyQt6.QtCore.qCritical(QCoreApplication.translate("MainWindow",
                "Some of your plugins have invalid names! These " +
                "plugins can not be loaded by the game. Please see " +
                "mo_interface.log for a list of affected plugins " +
                "and rename them."))

        if written_count == 0:
            PyQt6.QtCore.qWarning("plugin list would be empty, this is almost certainly wrong. Not saving.")
        else:
            plugins_file.write(plugins_text)
        plugins_file.close()

    def readLoadOrderList(self, plugin_list: mobase.IPluginList, file_path: str) -> list[str]:
        plugin_names = [plugin for plugin in self._organizer.managedGame().primaryPlugins()]
        plugin_lookup = set()
        for name in plugin_names:
            if name.lower() not in plugin_lookup:
                plugin_lookup.add(name.lower())

        try:
            with open(file_path) as file:
                for line in file:
                    if line.startswith('#'):
                        continue
                    plugin_file = line.rstrip('\n')
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
        plugin_remove = [plugin for plugin in plugins if plugin.lower() in primary_lower]
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
                if line.size() > 0 and line.at(0).decode() != '#':
                    encoder = QStringEncoder(QStringEncoder.Encoding.System)
                    file_plugin_name = encoder.encode(line.trimmed().data().decode())
                if file_plugin_name.size() > 0:
                    if file_plugin_name.data().decode().lower() in [plugin.lower() for plugin in plugins]:
                        plugin_list.setState(file_plugin_name.data().decode(), mobase.PluginState.ACTIVE)
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
        return 'obse64_loader.exe'

    def loaderName(self) -> str:
        return self.binaryName()

    def loaderPath(self) -> str:
        return self._game.gameDirectory().absolutePath() + '\\OblivionRemastered\\Binaries\\Win64\\' + self.loaderName()

    def pluginPath(self) -> str:
        return 'OBSE/Plugins'

    def savegameExtension(self) -> str:
        return ''

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
    UserHome = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.HomeLocation
    )
    GameSavesDirectory = r"{}\Documents\My Games\Oblivion Remastered\Saved\SaveGames".format(UserHome)
    GameSaveExtension = "sav"

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(BasicLocalSavegames(self.savesDirectory()))
        self._register_feature(BasicGameSaveGameInfo())
        self._register_feature(OblivionRemasteredGamePlugins(self._organizer))
        self._register_feature(OblivionRemasteredModDataChecker())
        self._register_feature(OblivionRemasteredScriptExtender(self))
        self.detectGame()
        paks_dir = QDir(self.gameDirectory().absolutePath() + r'\OblivionRemastered\Content\Paks')
        if paks_dir.exists() and not paks_dir.exists('~mods'):
            paks_dir.mkdir('~mods')
        return True

    def executables(self):
        qDebug(self._organizer.gameFeatures().gameFeature(mobase.ScriptExtender).loaderPath())
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
                    self._organizer.gameFeatures().gameFeature(mobase.ScriptExtender).loaderPath()
                )
            )
        ]

    def primaryPlugins(self) -> list[str]:
        return [
            'Oblivion.esm'
        ]

    def enabledPlugins(self) -> list[str]:
        return [
            'DLCBattlehornCastle.esp',
            'DLCFrostcrag.esp',
            'DLCHorseArmor.esp',
            'DLCMehrunesRazor.esp',
            'DLCOrrery.esp',
            'DLCShiveringIsles.esp',
            'DLCSpellTomes.esp',
            'DLCThievesDen.esp',
            'DLCVileLair.esp',
            'Knights.esp',
            'AltarESPMain.esp',
            'AltarDeluxe.esp',
            'AltarESPLocal.esp'
        ]

    def DLCPlugins(self) -> list[str]:
        return [
            'DLCBattlehornCastle.esp',
            'DLCFrostcrag.esp',
            'DLCHorseArmor.esp',
            'DLCMehrunesRazor.esp',
            'DLCOrrery.esp',
            'DLCShiveringIsles.esp',
            'DLCSpellTomes.esp',
            'DLCThievesDen.esp',
            'DLCVileLair.esp',
            'Knights.esp'
        ]

    def secondaryDataDirectories(self) -> Dict[str, QDir]:
        return {
            'pak_data': QDir(self.gameDirectory().absolutePath() + '/OblivionRemastered/Content/Paks/~mods')
        }

    def loadOrderMechanism(self) -> mobase.LoadOrderMechanism:
        return mobase.LoadOrderMechanism.PLUGINS_TXT

    def mappings(self) -> list[mobase.Mapping]:
        mappings: list[mobase.Mapping] = []
        for profile_file in ['plugins.txt', 'loadorder.txt']:
            mappings.append(mobase.Mapping(self._organizer.profilePath() + "/" + profile_file,
                                           self.dataDirectory().absolutePath() + "/" + profile_file,
                                           False))
        return mappings
