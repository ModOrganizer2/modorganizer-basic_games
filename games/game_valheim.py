# -*- encoding: utf-8 -*-

from __future__ import annotations

import fnmatch
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, fields
from typing import Optional

import mobase

from ..basic_game import BasicGame


def convert_entry_to_tree(entry: mobase.FileTreeEntry) -> Optional[mobase.IFileTree]:
    if not entry.isDir():
        return None
    if isinstance(entry, mobase.IFileTree):
        return entry
    if (parent := entry.parent()) is None:
        return None
    converted_entry = parent.find(
        entry.name(), mobase.FileTreeEntry.FileTypes.DIRECTORY
    )
    if isinstance(converted_entry, mobase.IFileTree):
        return converted_entry
    return None


@dataclass
class RegexFilesDefinition:
    """Regex pattern for the file lists in `FilesDefinition` - for globbing support.
    Fields should match `RegexFilesDefinition`.
    """

    set_as_root: re.Pattern
    valid: re.Pattern
    delete: re.Pattern
    move: re.Pattern

    @classmethod
    def from_filesmap(cls, filesdef: FilesDefinition) -> RegexFilesDefinition:
        """Returns an instance of `RegexFilesDefinition`,
        with the file list fields from `FilesDefinition` as regex patterns.
        """
        return cls(
            **{
                f.name: cls.file_list_regex(getattr(filesdef, f.name))
                for f in fields(cls)
            }
        )

    @classmethod
    def file_list_regex(cls, file_list: Iterable[str]) -> re.Pattern:
        """Returns a regex pattern for a file list with glob patterns.

        Every pattern has a capturing group,
        so that match.lastindex - 1 will give the file_list index.
        """
        return re.compile(
            f'(?:{"|".join(f"({fnmatch.translate(f)})" for f in file_list)})', re.I
        )


@dataclass
class FilesDefinition:
    """File (pattern) definitions for the `mobase.ModDataChecker`.
    Fields should match `RegexFilesDefinition`.
    """

    set_as_root: set[str]
    """If a folder from this set is found, it will be set as new root dir (unfolded)."""
    valid: set[str]
    """Files and folders in the right path."""
    delete: set[str]
    """Files/folders to delete."""
    move: dict[str, str]
    """Files/folders to move, like `{"*.ext": "path/to/folder/"}`.
        If the path ends with / or \\, the entry will be inserted
        in the corresponding directory instead of replacing it.
    """

    regex: RegexFilesDefinition = field(init=False)
    _move_targets: Sequence[str] = field(init=False)

    def __post_init__(self):
        self.regex = RegexFilesDefinition.from_filesmap(self)
        self._move_targets = list(self.move.values())

    def get_move_target(self, index: int) -> str:
        return self._move_targets[index]


class ValheimGameModDataChecker(mobase.ModDataChecker):
    files_map = FilesDefinition(
        set_as_root={
            "BepInExPack_Valheim",
        },
        valid={
            "meta.ini",  # Included in installed mod folder.
            "BepInEx",
            "doorstop_libs",
            "unstripped_corlib",
            "doorstop_config.ini",
            "start_game_bepinex.sh",
            "start_server_bepinex.sh",
            "winhttp.dll",
            #
            "InSlimVML",
            "valheim_Data",
            "inslimvml.ini",
            #
            "unstripped_managed",
            #
            "AdvancedBuilder",
        },
        delete={
            "*.txt",
            "*.md",
            "icon.png",
            "license",
            "manifest.json",
        },
        move={
            "*_VML.dll": "InSlimVML/Mods/",
            #
            "plugins": "BepInEx/",
            "*.dll": "BepInEx/plugins/",
            "config": "BepInEx/",
            "*.cfg": "BepInEx/config/",
            #
            "CustomTextures": "BepInEx/plugins/",
            "*.png": "BepInEx/plugins/CustomTextures/",
            #
            "Builds": "AdvancedBuilder/",
            "*.vbuild": "AdvancedBuilder/Builds/",
            #
            "*.assets": "valheim_Data/",
        },
    )

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        status = mobase.ModDataChecker.INVALID
        for entry in filetree:
            name = entry.name().casefold()
            if self.files_map.regex.set_as_root.match(name):
                status = mobase.ModDataChecker.FIXABLE
            elif self.files_map.regex.valid.match(name):
                if status is not mobase.ModDataChecker.FIXABLE:
                    status = mobase.ModDataChecker.VALID
            elif self.files_map.regex.move.match(
                name
            ) or self.files_map.regex.delete.match(name):
                status = mobase.ModDataChecker.FIXABLE
            else:
                return mobase.ModDataChecker.INVALID
        return status

    def fix(self, filetree: mobase.IFileTree) -> Optional[mobase.IFileTree]:
        for entry in list(filetree):
            name = entry.name().casefold()
            if self.files_map.regex.set_as_root.match(name):
                new_root = convert_entry_to_tree(entry)
                if not new_root:
                    return None
                return self.fix(new_root)
            elif self.files_map.regex.delete.match(name):
                entry.detach()
            elif match := self.files_map.regex.move.match(name):
                if match.lastindex is not None:
                    # Get index of matched group
                    map_index = match.lastindex - 1
                    # Get the move target corresponding to the matched group
                    filetree.move(entry, self.files_map.get_move_target(map_index))
        return filetree


class ValheimGame(BasicGame):

    Name = "Valheim Support Plugin"
    Author = "Zash"
    Version = "1.0.0"

    GameName = "Valheim"
    GameShortName = "valheim"
    GameNexusId = 3667
    GameSteamId = [892970, 896660, 1223920]
    GameBinary = "valheim.exe"
    GameDataPath = ""

    forced_libraries = ["winhttp.dll"]

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = ValheimGameModDataChecker()
        return True

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        return [
            mobase.ExecutableForcedLoadSetting(self.binaryName(), lib).withEnabled(True)
            for lib in self.forced_libraries
        ]
