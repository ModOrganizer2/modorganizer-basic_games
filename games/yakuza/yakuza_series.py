from __future__ import annotations

import os
import shutil
import time
import webbrowser
from typing import Optional

import mobase
from PyQt5.QtCore import qWarning
from PyQt5.QtWidgets import QMessageBox

from ...basic_game import BasicGame


def yakuza_check_rmm(plugin: BasicGame, win):
    if not plugin.isActive():
        return

    rmm_path = os.path.join(plugin._gamePath, os.path.dirname(plugin.GameBinary), 'RyuModManager.exe')

    if not os.path.exists(rmm_path):
        reply = QMessageBox.critical(
            win,
            'Ryu Mod Manager Missing',
            'Ryu Mod Manager was not found in the game\'s directory. Mods will not work without it.\nOpen Ryu Mod Manager download page?',
            QMessageBox.Yes | QMessageBox.Ignore,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            webbrowser.open('https://github.com/SutandoTsukai181/RyuModManager/releases/latest')


def yakuza_import_mods(plugin: BasicGame, win):
    if not plugin.isActive() or (plugin._organizer.pluginSetting(plugin.name(), 'import_mods_prompt') is False):
        return

    game_mods_path = os.path.join(plugin._gamePath, os.path.dirname(plugin.GameDataPath))

    success_count = 0
    fail_count = 0

    # Get the installed mods
    modfolders = [x for x in os.listdir(game_mods_path) if os.path.isdir(
        os.path.join(game_mods_path, x)) and x not in ('Parless', '_externalMods')]

    # Ask if we should migrate mods
    reply = QMessageBox.question(
        win,
        'Import Mods',
        'Do you want to import your Ryu Mod Manager mods to Mod Organizer?\nDoing so will move all the mods and delete them from the original directory.',
        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        QMessageBox.Cancel
    )

    if reply == QMessageBox.Cancel:
        # Just stop, and show the same prompt next time
        return

    # If the reply is either Yes or No, then we don't want to show this prompt next time
    plugin._organizer.setPluginSetting(plugin.name(), 'import_mods_prompt', False)

    if reply == QMessageBox.No:
        QMessageBox.information(
            win,
            'Import Mods',
            'Mods will NOT be imported. If you want to see this prompt again, you can change the option in the plugin settings.',
            QMessageBox.Ok,
            QMessageBox.Ok
        )

        return

    # Read mod list file and sort the mods accordingly
    enabled_mods = None
    modlist = os.path.join(os.path.dirname(game_mods_path), 'ModList.txt')
    if os.path.exists(modlist) and os.path.isfile(modlist):
        with open(modlist) as file:
            # List of mods to enable after importing is done
            enabled_mods = [(x[1:], x[0] == '<') for x in file.readline().rstrip('\n').split('|') if x.startswith('<') or x.startswith('>')]
            ordered_mods, _ = zip(*enabled_mods)
            enabled_mods = dict([x for x in enabled_mods if x[1]])

            # Sort the folders according to the order in the list
            modfolders.sort(key=(lambda k: (val := dict(zip(ordered_mods, range(len(ordered_mods)))).get(k))
                                 or (val if val is not None else len(ordered_mods))))

    # -1 for the overwrite folder
    org_mod_count = len(plugin._organizer.modList().allMods()) - 1

    # Import mods
    for mod_name in modfolders:
        mod_path = os.path.join(game_mods_path, mod_name)

        try:
            mod = plugin._organizer.createMod(mobase.GuessedString(mod_name))
            shutil.copytree(mod_path, mod.absolutePath(), dirs_exist_ok=True)

            # Should not call IOrganizer.modDataChanged() because all it does is start a refresh
            # and it won't finish before the script is done anyway

            success_count += 1
        except Exception:
            fail_count += 1
            qWarning(f'Could not properly import mod: {mod_name}')

        try:
            shutil.rmtree(mod_path, ignore_errors=True)
        except Exception:
            qWarning(f'Could not remove mod after importing from path: {mod_path}')

    # 3 seconds seems appropriate
    plugin._organizer.refresh(False)
    time.sleep(3)

    for i, mod_name in enumerate(modfolders):
        # Set each mod according to its ordered priority
        p = org_mod_count + i
        plugin._organizer.modList().setPriority(mod_name, p)
        plugin._organizer.modList().setActive(mod_name, enabled_mods.get(mod_name, False))

    # Manual refresh is needed for some reason
    # Maybe something about the refresh not being able to finish until after the script is done?
    # no matter how much time you sleep, it won't finish
    if reply == QMessageBox.Yes:
        QMessageBox.information(
            win,
            'Success',
            f'{success_count} mod(s) have been imported.\n' +
            (f'{fail_count} mod(s) could not be imported.\n' if fail_count > 0 else '') +
            '\nPlease refresh the mod list manually (Right click -> "Refresh")',
            QMessageBox.Ok,
            QMessageBox.Ok
        )


class YakuzaGameModDataChecker(mobase.ModDataChecker):

    def __init__(self, valid_paths: set):
        super().__init__()
        self._validPaths = valid_paths

    _validPaths: set

    def walk_tree(self, filetree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        name = filetree.name().casefold()

        if name in self._validPaths:
            return mobase.ModDataChecker.FIXABLE

        if filetree.isDir():
            for entry in filetree:
                if self.walk_tree(entry) != mobase.ModDataChecker.INVALID:
                    return mobase.ModDataChecker.FIXABLE

        return mobase.ModDataChecker.INVALID

    def dataLooksValid(self, filetree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        # Check for mods that were already installed
        for entry in filetree:
            if entry.name().casefold() in self._validPaths:
                return mobase.ModDataChecker.VALID

        return self.walk_tree(filetree)

    def fix(self, filetree: mobase.IFileTree) -> Optional[mobase.IFileTree]:
        name = filetree.name().casefold()

        if name in self._validPaths and filetree.parent() is not None:
            return filetree.parent()

        # Keep looking for a valid path
        if filetree.isDir():
            for entry in filetree:
                result = self.fix(entry)
                if result is not None:
                    return result

        return None
