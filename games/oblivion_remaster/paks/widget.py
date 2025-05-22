import re
from functools import cmp_to_key
from pathlib import Path
from typing import cast

from PyQt6.QtCore import QDir, QFileInfo, qDebug
from PyQt6.QtWidgets import QGridLayout, QWidget

import mobase

from ....basic_features.utils import is_directory
from .model import PaksModel, _PakInfo
from .view import PaksView


def pak_sort(a: tuple[str, str], b: tuple[str, str]) -> int:
    a_pak, a_str = a[0], a[1] or a[0]
    b_pak, b_str = b[0], b[1] or b[0]

    a_pak_ends_p = a_pak.casefold().endswith("_p")
    b_pak_ends_p = b_pak.casefold().endswith("_p")

    if a_pak_ends_p == b_pak_ends_p:
        if a_str.casefold() <= b_str.casefold():
            return 1
        return -1
    elif a_pak_ends_p:
        return 1
    elif b_pak_ends_p:
        return -1
    return 0


class PaksTabWidget(QWidget):
    def __init__(self, parent: QWidget | None, organizer: mobase.IOrganizer):
        super().__init__(parent)
        self._organizer = organizer
        self._view = PaksView(self)
        self._layout = QGridLayout(self)
        self._layout.addWidget(self._view)
        self._model = PaksModel(self._view, organizer)
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
        paks_txt = QFileInfo(profile.absoluteFilePath("paks.txt"))
        paks_list: list[str] = []
        if paks_txt.exists():
            with open(paks_txt.absoluteFilePath(), "r") as paks_file:
                for line in paks_file:
                    paks_list.append(line.strip())
        return paks_list

    def write_paks_list(self):
        profile = QDir(self._organizer.profilePath())
        paks_txt = QFileInfo(profile.absoluteFilePath("paks.txt"))
        with open(paks_txt.absoluteFilePath(), "w") as paks_file:
            for _, pak in sorted(self._model.paks.items()):
                name, _, _, _ = pak
                paks_file.write(f"{name}\n")
        self.write_pak_files()

    def write_pak_files(self):
        for index, pak in sorted(self._model.paks.items()):
            name, _, current_path, target_path = pak
            if current_path and current_path != target_path:
                path_dir = Path(current_path)
                target_dir = Path(target_path)
                if not target_dir.exists():
                    target_dir.mkdir(parents=True, exist_ok=True)
                if path_dir.exists():
                    for pak_file in path_dir.glob("*.pak"):
                        match = re.match(r"^(\d{4}_)?(.*)", pak_file.stem)
                        if not match:
                            continue
                        match_name = (
                            match.group(2) if match.group(2) else match.group(1)
                        )
                        if match_name == name:
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
        shaken_paks: list[str] = []
        shaken_paks_p: list[str] = []
        paks_list = self.load_paks_list()
        qDebug("Read paks...")
        for pak in paks_list:
            qDebug(pak)
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
        from ...game_oblivion_remaster import OblivionRemasteredGame

        mods = self._organizer.modList().allMods()
        paks: dict[str, str] = {}
        pak_paths: dict[str, tuple[str, str]] = {}
        pak_source: dict[str, str] = {}
        for mod in mods:
            mod_item = self._organizer.modList().getMod(mod)
            if not self._organizer.modList().state(mod) & mobase.ModState.ACTIVE:
                continue
            filetree = mod_item.fileTree()
            pak_mods = filetree.find("Paks/~mods")
            if not pak_mods:
                pak_mods = filetree.find("Root/OblivionRemastered/Content/Paks/~mods")
            if isinstance(pak_mods, mobase.IFileTree):
                for entry in pak_mods:
                    if is_directory(entry):
                        if entry.name().casefold() == "magicloader":
                            continue
                        for sub_entry in entry:
                            if (
                                sub_entry.isFile()
                                and sub_entry.suffix().casefold() == "pak"
                            ):
                                paks[
                                    sub_entry.name()[: -1 - len(sub_entry.suffix())]
                                ] = entry.name()
                                pak_paths[
                                    sub_entry.name()[: -1 - len(sub_entry.suffix())]
                                ] = (
                                    mod_item.absolutePath()
                                    + "/"
                                    + cast(mobase.IFileTree, sub_entry.parent()).path(
                                        "/"
                                    ),
                                    mod_item.absolutePath() + "/" + pak_mods.path("/"),
                                )
                                pak_source[
                                    sub_entry.name()[: -1 - len(sub_entry.suffix())]
                                ] = mod_item.name()
                    else:
                        if entry.suffix().casefold() == "pak":
                            paks[entry.name()[: -1 - len(entry.suffix())]] = ""
                            pak_paths[entry.name()[: -1 - len(entry.suffix())]] = (
                                mod_item.absolutePath()
                                + "/"
                                + cast(mobase.IFileTree, entry.parent()).path("/"),
                                mod_item.absolutePath() + "/" + pak_mods.path("/"),
                            )
                            pak_source[entry.name()[: -1 - len(entry.suffix())]] = (
                                mod_item.name()
                            )
        game = self._organizer.managedGame()
        if isinstance(game, OblivionRemasteredGame):
            pak_mods = QFileInfo(game.paksDirectory().absoluteFilePath("~mods"))
            if pak_mods.exists() and pak_mods.isDir():
                for entry in QDir(pak_mods.absoluteFilePath()).entryInfoList(
                    QDir.Filter.Dirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot
                ):
                    if entry.isDir():
                        if entry.completeBaseName().casefold() == "magicloader":
                            continue
                        for sub_entry in QDir(entry.absoluteFilePath()).entryInfoList(
                            QDir.Filter.Files
                        ):
                            if (
                                sub_entry.isFile()
                                and sub_entry.suffix().casefold() == "pak"
                            ):
                                paks[sub_entry.completeBaseName()] = (
                                    entry.completeBaseName()
                                )
                                pak_paths[sub_entry.completeBaseName()] = (
                                    sub_entry.absolutePath(),
                                    pak_mods.absolutePath(),
                                )
                                pak_source[sub_entry.completeBaseName()] = (
                                    "Game Directory"
                                )
                    else:
                        if entry.suffix().casefold() == "pak":
                            paks[
                                entry.completeBaseName()[: -1 - len(entry.suffix())]
                            ] = ""
                            pak_paths[entry.completeBaseName()] = (
                                entry.absolutePath(),
                                pak_mods.absolutePath(),
                            )
                            pak_source[entry.completeBaseName()] = "Game Directory"
        sorted_paks = dict(sorted(paks.items(), key=cmp_to_key(pak_sort)))
        shaken_paks: list[str] = self._shake_paks(sorted_paks)
        qDebug("Shaken paks:")
        for pak in shaken_paks:
            qDebug(pak)
        final_paks: dict[str, tuple[str, str, str]] = {}
        pak_index = 9999
        for pak in shaken_paks:
            target_dir = pak_paths[pak][1] + "/" + str(pak_index).zfill(4)
            final_paks[pak] = (pak_source[pak], pak_paths[pak][0], target_dir)
            pak_index -= 1
        new_data_paks: dict[int, _PakInfo] = {}
        i = 0
        for pak, data in final_paks.items():
            source, current_path, target_path = data
            new_data_paks[i] = (pak, source, current_path, target_path)
            i += 1
        self._model.set_paks(new_data_paks)
