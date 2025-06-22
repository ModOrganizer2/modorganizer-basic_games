import os
from functools import cmp_to_key
from pathlib import Path
from typing import List, Tuple, cast

from PyQt6.QtCore import QDir, QFileInfo
from PyQt6.QtWidgets import QGridLayout, QWidget

import mobase

from ....basic_features.utils import is_directory
from .model import S2HoCPaksModel
from .view import S2HoCPaksView


def pak_sort(a: tuple[str, str], b: tuple[str, str]) -> int:
    """Sort function for PAK files (like Oblivion Remastered)"""
    if a[0] < b[0]:
        return -1
    elif a[0] > b[0]:
        return 1
    else:
        return 0


class S2HoCPaksTabWidget(QWidget):
    """
    Widget for managing PAK files in Stalker 2: Heart of Chornobyl.
    """

    def __init__(self, parent: QWidget, organizer: mobase.IOrganizer):
        super().__init__(parent)
        self._organizer = organizer
        self._view = S2HoCPaksView(self)
        self._layout = QGridLayout(self)
        self._layout.addWidget(self._view)
        self._model = S2HoCPaksModel(self._view, organizer)
        self._view.setModel(self._model)
        self._model.dataChanged.connect(self.write_paks_list)  # type: ignore
        self._view.data_dropped.connect(self.write_paks_list)  # type: ignore
        organizer.onProfileChanged(lambda profile_a, profile_b: self._parse_pak_files())
        organizer.modList().onModInstalled(lambda mod: self._parse_pak_files())
        organizer.modList().onModRemoved(lambda mod: self._parse_pak_files())
        organizer.modList().onModStateChanged(lambda mods: self._parse_pak_files())
        self._parse_pak_files()

    def load_paks_list(self) -> list[str]:
        profile = QDir(self._organizer.profilePath())
        paks_txt = QFileInfo(profile.absoluteFilePath("stalker2_paks.txt"))
        paks_list: list[str] = []
        if paks_txt.exists():
            with open(paks_txt.absoluteFilePath(), "r") as paks_file:
                for line in paks_file:
                    paks_list.append(line.strip())
        return paks_list

    def write_paks_list(self):
        """Write the PAK list to file and then move the files"""
        profile = QDir(self._organizer.profilePath())
        paks_txt = QFileInfo(profile.absoluteFilePath("stalker2_paks.txt"))
        with open(paks_txt.absoluteFilePath(), "w") as paks_file:
            for _, pak in sorted(self._model.paks.items()):
                name, _, _, _ = pak
                paks_file.write(f"{name}\n")
        # Also move the files after updating the list
        self.write_pak_files()

    def write_pak_files(self):
        """Move PAK files to their target numbered directories"""
        for index, pak in sorted(self._model.paks.items()):
            _, _, current_path, target_path = pak
            if current_path and current_path != target_path:
                path_dir = Path(current_path)
                target_dir = Path(target_path)
                if not target_dir.exists():
                    target_dir.mkdir(parents=True, exist_ok=True)
                if path_dir.exists():
                    for pak_file in path_dir.glob("*.pak"):
                        ucas_file = pak_file.with_suffix(".ucas")
                        utoc_file = pak_file.with_suffix(".utoc")
                        for file in (pak_file, ucas_file, utoc_file):
                            if not file.exists():
                                continue
                            try:
                                file.rename(target_dir.joinpath(file.name))
                            except FileExistsError:
                                pass
                        data = self._model.paks[index]
                        self._model.paks[index] = (
                            data[0],
                            data[1],
                            data[3],
                            data[3],
                        )
                        break
                    if not list(path_dir.iterdir()):
                        path_dir.rmdir()

    def _shake_paks(self, sorted_paks: dict[str, str]) -> list[str]:
        """Preserve order from paks.txt if it exists, otherwise use alphabetical (like Oblivion Remastered)"""
        shaken_paks: list[str] = []
        shaken_paks_p: list[str] = []
        paks_list = self.load_paks_list()
        for pak in paks_list:
            if pak in sorted_paks.keys():
                if pak.casefold().endswith("_p"):
                    shaken_paks_p.append(pak)
                else:
                    shaken_paks.append(pak)
                sorted_paks.pop(pak)
        for pak in sorted_paks.keys():
            if pak.casefold().endswith("_p"):
                shaken_paks_p.append(pak)
            else:
                shaken_paks.append(pak)
        return shaken_paks + shaken_paks_p

    def _parse_pak_files(self):
        """Parse PAK files from mods, following Oblivion Remastered pattern for numbered folder assignment"""
        from ...game_stalker2heartofchornobyl import S2HoCGame

        mods = self._organizer.modList().allMods()
        paks: dict[str, str] = {}
        pak_paths: dict[str, tuple[str, str]] = {}
        pak_source: dict[str, str] = {}
        existing_folders: set[int] = set()
        
        print(f"[PAK Debug] Starting scan of {len(mods)} mods")
        print(f"[PAK Debug] ONLY scanning ~mods directories, EXCLUDING LogicMods")
        
        # First, scan what numbered folders already exist to avoid double-assignment
        game = self._organizer.managedGame()
        if isinstance(game, S2HoCGame):
            pak_mods_dir = QFileInfo(game.paksModsDirectory().absolutePath())
            if pak_mods_dir.exists() and pak_mods_dir.isDir():
                print(f"[PAK Debug] Scanning existing folders in: {pak_mods_dir.absoluteFilePath()}")
                for entry in QDir(pak_mods_dir.absoluteFilePath()).entryInfoList(
                    QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot
                ):
                    try:
                        folder_num = int(entry.completeBaseName())
                        existing_folders.add(folder_num)
                        print(f"[PAK Debug] Found existing numbered folder: {folder_num}")
                    except ValueError:
                        print(f"[PAK Debug] Skipping non-numbered folder: {entry.completeBaseName()}")
        
        # Scan mods for PAK files ONLY in Content/Paks/~mods structure (exclude LogicMods)
        for mod in mods:
            mod_item = self._organizer.modList().getMod(mod)
            if not self._organizer.modList().state(mod) & mobase.ModState.ACTIVE:
                continue
            filetree = mod_item.fileTree()

            # If this mod contains a LogicMods directory, skip it entirely for the PAK tab
            has_logicmods = (
                filetree.find("Content/Paks/LogicMods") or filetree.find("Paks/LogicMods")
            )
            if isinstance(has_logicmods, mobase.IFileTree):
                print(f"[PAK Debug] Skipping mod '{mod_item.name()}' because it contains a LogicMods directory.")
                continue

            # ONLY look for ~mods directories
            pak_mods = filetree.find("Paks/~mods")
            if not pak_mods:
                pak_mods = filetree.find("Content/Paks/~mods")
            if isinstance(pak_mods, mobase.IFileTree) and pak_mods.name() == "~mods":
                print(f"[PAK Debug]   Found ~mods directory in: {mod_item.name()}")
                for entry in pak_mods:
                    if is_directory(entry):
                        for sub_entry in entry:
                            if (
                                sub_entry.isFile()
                                and sub_entry.suffix().casefold() == "pak"
                            ):
                                pak_name = sub_entry.name()[: -1 - len(sub_entry.suffix())]
                                paks[pak_name] = entry.name()
                                pak_paths[pak_name] = (
                                    mod_item.absolutePath()
                                    + "/"
                                    + cast(mobase.IFileTree, sub_entry.parent()).path("/"),
                                    mod_item.absolutePath() + "/" + pak_mods.path("/")
                                )
                                pak_source[pak_name] = mod_item.name()
                                print(f"[PAK Debug]   ✅ Added PAK from ~mods numbered folder: {pak_name} in {entry.name()}")
                    else:
                        if entry.suffix().casefold() == "pak":
                            pak_name = entry.name()[: -1 - len(entry.suffix())]
                            paks[pak_name] = ""
                            pak_paths[pak_name] = (
                                mod_item.absolutePath()
                                + "/"
                                + cast(mobase.IFileTree, entry.parent()).path("/"),
                                mod_item.absolutePath() + "/" + pak_mods.path("/")
                            )
                            pak_source[pak_name] = mod_item.name()
                            print(f"[PAK Debug]   ✅ Added loose PAK from ~mods: {pak_name}")
            else:
                # Check if this mod has LogicMods (for debugging purposes)
                logic_mods = filetree.find("Content/Paks/LogicMods")
                if not logic_mods:
                    logic_mods = filetree.find("Paks/LogicMods")
                if isinstance(logic_mods, mobase.IFileTree):
                    print(f"[PAK Debug]   Mod {mod_item.name()} has LogicMods (not included in PAK tab)")

        # NOTE: Removed game directory scanning to prevent LogicMods PAKs from appearing
        # We only want PAKs from mod files, not from game directory
        print(f"[PAK Debug] Skipping game directory scan to prevent LogicMods inclusion")

        # Sort PAKs and shake them (preserve order from paks.txt if it exists)
        sorted_paks = dict(sorted(paks.items(), key=cmp_to_key(pak_sort)))
        shaken_paks: list[str] = self._shake_paks(sorted_paks)
        
        # Assign target directories with numbered folders (like Oblivion Remastered)
        # Skip numbers that already exist, use next available number starting from 8999
        final_paks: dict[str, tuple[str, str, str]] = {}
        pak_index = 8999
        
        for pak in shaken_paks:
            # Find next available number (skip existing folders)
            while pak_index in existing_folders:
                pak_index -= 1
            
            # If PAK is already in a numbered folder, keep its current assignment
            current_folder = paks[pak]
            if current_folder.isdigit():
                target_dir = pak_paths[pak][1] + "/" + current_folder
                existing_folders.add(int(current_folder))
                print(f"[PAK Debug] Keeping {pak} in existing folder {current_folder}")
            else:
                # Assign new numbered folder for loose PAKs
                target_dir = pak_paths[pak][1] + "/" + str(pak_index).zfill(4)
                existing_folders.add(pak_index)
                print(f"[PAK Debug] Assigning {pak} to new folder {pak_index}")
                pak_index -= 1
            
            final_paks[pak] = (pak_source[pak], pak_paths[pak][0], target_dir)
        
        # Convert to model format (4-tuple matching Oblivion Remastered)
        new_data_paks: dict[int, tuple[str, str, str, str]] = {}
        i = 0
        for pak, data in final_paks.items():
            source, current_path, target_path = data
            new_data_paks[i] = (pak, source, current_path, target_path)
            i += 1
        
        print(f"[PAK Debug] Final PAK count: {len(new_data_paks)}")
        self._model.set_paks(new_data_paks)
