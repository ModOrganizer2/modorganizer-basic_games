# -*- encoding: utf-8 -*-

from __future__ import annotations

import fnmatch
import itertools
import re
import shutil
from collections.abc import Collection, Container, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Optional, TextIO, Union

from PyQt5.QtCore import QDir

import mobase

from ..basic_features.basic_save_game_info import BasicGameSaveGame
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


def move_file(source: Path, target: Path):
    """Move `source` to `target`. Creates missing (parent) directories and
    overwrites existing `target`."""
    if not target.parent.exists():
        target.parent.mkdir(parents=True)
    shutil.move(str(source.resolve()), str(target.resolve()))


@dataclass
class PartialMatch:
    partial_match_regex: re.Pattern = re.compile(r"[A-Z]?[a-z]+")
    """Matches words, for e.g. 'Camel' and 'Case' in 'CamelCase'."""

    exclude: Container = field(default_factory=set)
    min_length: int = 3

    def partial_match(self, str_with_parts: str, search_string: str) -> Collection[str]:
        """Returns partial matches of the first string (`str_with_parts`)
        in the `search_string`.

        See:
            `partial_match_regex`
        """
        parts = self.partial_match_regex.finditer(str_with_parts)
        search_string_lower = search_string.casefold()
        return set(
            p_lower
            for p in parts
            if len(p_lower := p[0].casefold()) >= self.min_length
            and p_lower not in self.exclude
            and p_lower in search_string_lower
        )


@dataclass
class ContentMatch:
    file_glob_patterns: Iterable[str]
    """File patterns (glob) for content files and `content_regex`."""
    content_regex: re.Pattern[str]
    """Regex to get mod name from content. with (?P<`match_group`>) group."""
    match_group: str

    def match_content(self, file_path: Path) -> str:
        if (
            self.content_regex
            and self.file_glob_patterns
            and any(file_path.match(p) for p in self.file_glob_patterns)
        ):
            with open(file_path) as file:
                if match := self.content_regex.search(file.read()):
                    return match.group(self.match_group)
        return ""


class DebugTable:
    """Debug in markdown table."""

    def __init__(self, column_keys: Collection[str]) -> None:
        """Init the table, adds the header.

        Args:
            column_keys: The column keys for the table.
        """
        self.new_table(column_keys)

    def __call__(self, **kwargs) -> None:
        self.add(**kwargs)

    def new_table(self, column_keys: Optional[Collection[str]] = None) -> None:
        if column_keys:
            self._column_keys = column_keys
        self._table: list[dict[str, str]] = [
            {c: c for c in self._column_keys},
            {c: "-" * len(c) for c in self._column_keys},
        ]

    def add(
        self,
        **kwargs,
    ) -> None:
        """Add data to the table. Adds a new line if the last row has already data in
        for the column key.

        Args:
            **kwargs: the values per column key for a row.
        """
        for k, v in kwargs.items():
            if not self._table or self._table[-1].get(k, ""):
                # Append line if element in last list is set.
                self._table.append(dict.fromkeys(self._column_keys, ""))
            self._table[-1][k] = str(v)

    def print(self, output_file: Optional[TextIO] = None):
        if self._table:
            for line in self._table:
                print("|", " | ".join(line.values()), "|", file=output_file)
            output_file and output_file.flush()
            self._table = []


class OverwriteSync:
    organizer: mobase.IOrganizer
    game: mobase.IPluginGame
    search_file_contents: bool = True

    overwrite_file_pattern: Iterable[str] = ["BepInEx/config/*"]
    """File pattern (glob) in overwrite folder."""
    partial_match: PartialMatch = PartialMatch(exclude={"valheim", "mod"})
    content_match: Optional[ContentMatch] = ContentMatch(
        file_glob_patterns=["*.cfg"],
        content_regex=re.compile(r"\A.*plugin (?P<mod>.+) v[\d\.]+?$", re.I | re.M),
        match_group="mod",
    )

    _debug = DebugTable("overwrite_file | mod | target_path | matches".split(" | "))

    def __init__(self, organizer: mobase.IOrganizer, game: mobase.IPluginGame) -> None:
        self.organizer = organizer
        self.game = game

    def sync(self) -> None:
        """Sync the Overwrite folder (back) to the mods."""
        print("Syncing Overwrite with mods")
        modlist = self.organizer.modList()
        mod_map = self._get_active_mods(modlist)
        mod_dll_map = self._get_mod_dll_map(mod_map)
        overwrite_path = Path(self.organizer.overwritePath())
        self._debug.new_table()
        for pattern in self.overwrite_file_pattern:
            for file_path in overwrite_path.glob(pattern):
                self._debug(overwrite_file=file_path.name)
                if mod := self._find_mod_for_overwrite_file(file_path, mod_dll_map):
                    # Move cfg to mod folder
                    mod_path = Path(modlist.getMod(mod).absolutePath())
                    target_path = mod_path / file_path.relative_to(overwrite_path)
                    self._debug(mod=mod, target_path=target_path)
                    move_file(file_path, target_path)
                self._debug.print()

    def _get_active_mods(
        self, modlist: Optional[mobase.IModList] = None
    ) -> Mapping[str, mobase.IModInterface]:
        """Get all active mods.

        Args: modlist (optional): the `mobase.IModList`. Defaults to None (get it from
            `self._organizer`).

        Returns: `{mod_name: mobase.IModInterface}`
        """
        modlist = modlist or self.organizer.modList()

        return {
            name: mod
            for name in modlist.allMods()  # allModsByProfilePriority ?
            if (mod := modlist.getMod(name)).gameName() == self.game.gameShortName()
            and not mod.isForeign()
            and not mod.isBackup()
            and not mod.isSeparator()
            and (modlist.state(name) & mobase.ModState.ACTIVE)
        }

    def _get_mod_dll_map(self, mod_map):
        return {name: self._get_mod_dlls(mod) for name, mod in mod_map.items()}

    def _get_mod_dlls(self, mod: Union[str, mobase.IModInterface]) -> Sequence[str]:
        """Get all BepInEx/plugins/*.dll files of a mod."""
        if isinstance(mod, str):
            mod = self.organizer.modList().getMod(mod)
        plugins = mod.fileTree().find("BepInEx/plugins/", mobase.IFileTree.DIRECTORY)
        if isinstance(plugins, mobase.IFileTree):
            return [name for p in plugins if (name := p.name()).endswith(".dll")]
        else:
            return []

    def _find_mod_for_overwrite_file(
        self,
        file_path: Path,
        mod_dll_map: Mapping[str, Collection[str]],
    ) -> str:
        """Find the mod (name) matching a file in Overwrite (using the mods dll name).

        Args:
            file_name: The name of the file.
            mod_dll_map: Mods names and their dll files `{mod_name: ["ModName.dll"]}`.

        Returns:
            The name of the mod matching the given file_name best.
            If there is no clear mod match for the file, an empty string "" is returned.
        """
        if file_path.is_dir():
            return ""
        file_name = file_path.stem
        # matching metric: combined length of partial matches per mod.
        matching_mods = self._get_matching_mods(file_name, mod_dll_map)
        if len(matching_mods) == 0:
            if self.search_file_contents and self.content_match:
                # Get mod name from file content.
                long_mod_name = self.content_match.match_content(file_path)
                matching_mods = self._get_matching_mods(long_mod_name, mod_dll_map)
        if len(matching_mods) == 1:
            # Only a single mod match found.
            return matching_mods[0][0]
        elif len(matching_mods) > 1:
            # Find mod with longest (combined) partial_match.
            self._debug.add(matches=matching_mods)
            # Do not return a mod for multiple "equal" matches.
            if matching_mods[0][1] > matching_mods[1][1]:
                return matching_mods[0][0]
        return ""

    def _get_matching_mods(
        self, search_str: str, mod_dll_map: Mapping[str, Collection[str]]
    ) -> Sequence[tuple[str, int, set[str]]]:
        """Find matching mods for the given `search_str`.

        Args:
            search_name: A string to find a mod match for. mod_dll_map: Mods names and
            their dll files `{mod_name: ["ModName.dll"]}`.

        Returns:
            Mods with partial matches, sorted descending by their metric
            (length of combined partial matches):
            {mod_name: (len_of_combined_partial_matches, {partial_matches, ...}), ...}
        """
        return sorted(
            (
                (name, sum(len(s) for s in partial_matches), partial_matches)
                for name, dlls in mod_dll_map.items()
                if len(
                    partial_matches := set(
                        itertools.chain.from_iterable(
                            self.partial_match.partial_match(search_str, dll)
                            for dll in dlls
                        )
                    )
                )
                > 0
            ),
            key=lambda x: x[1],
            reverse=True,
        )


@dataclass
class RegexFilesDefinition:
    """Regex pattern for the file lists in `FilesDefinition` - for globbing support.
    Fields should match `RegexFilesDefinition`.
    """

    set_as_root: Optional[re.Pattern]
    valid: Optional[re.Pattern]
    delete: Optional[re.Pattern]
    move: Optional[re.Pattern]

    @classmethod
    def from_filesmap(cls, filesdef: FilesDefinition) -> RegexFilesDefinition:
        """Returns an instance of `RegexFilesDefinition`,
        with the file list fields from `FilesDefinition` as regex patterns.
        """
        return cls(
            **{
                f.name: (
                    cls.file_list_regex(value)
                    if (value := getattr(filesdef, f.name))
                    else None
                )
                for f in fields(cls)
            }
        )

    @staticmethod
    def file_list_regex(file_list: Iterable[str]) -> re.Pattern:
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

    set_as_root: Optional[set[str]]
    """If a folder from this set is found, it will be set as new root dir (unfolded)."""
    valid: Optional[set[str]]
    """Files and folders in the right path."""
    delete: Optional[set[str]]
    """Files/folders to delete."""
    move: Optional[dict[str, str]]
    """Files/folders to move, like `{"*.ext": "path/to/folder/"}`.
        If the path ends with / or \\, the entry will be inserted
        in the corresponding directory instead of replacing it.
    """

    regex: RegexFilesDefinition = field(init=False)
    _move_targets: Sequence[str] = field(init=False, repr=False)

    def __post_init__(self):
        self.regex = RegexFilesDefinition.from_filesmap(self)
        if self.move:
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
            regex = self.files_map.regex
            if regex.set_as_root and regex.set_as_root.match(name):
                return mobase.ModDataChecker.FIXABLE
            elif regex.valid and regex.valid.match(name):
                if status is not mobase.ModDataChecker.FIXABLE:
                    status = mobase.ModDataChecker.VALID
            elif (regex.move and regex.move.match(name)) or (
                regex.delete and regex.delete.match(name)
            ):
                status = mobase.ModDataChecker.FIXABLE
            else:
                return mobase.ModDataChecker.INVALID
        return status

    def fix(self, filetree: mobase.IFileTree) -> Optional[mobase.IFileTree]:
        for entry in list(filetree):
            name = entry.name().casefold()
            regex = self.files_map.regex
            if regex.set_as_root and regex.set_as_root.match(name):
                new_root = convert_entry_to_tree(entry)
                return self.fix(new_root) if new_root else None
            elif regex.valid and regex.valid.match(name):
                continue
            elif regex.delete and regex.delete.match(name):
                entry.detach()
            elif regex.move and (match := regex.move.match(name)):
                if match.lastindex is None:
                    return None
                else:
                    # Get index of matched group
                    map_index = match.lastindex - 1
                    # Get the move target corresponding to the matched group
                    filetree.move(entry, self.files_map.get_move_target(map_index))
        return filetree


class ValheimSaveGame(BasicGameSaveGame):
    def getName(self) -> str:
        return f"[{self.getSaveGroupIdentifier().rstrip('s')}] {self._filepath.stem}"

    def getSaveGroupIdentifier(self) -> str:
        return self._filepath.parent.name

    def allFiles(self) -> list[str]:
        files = super().allFiles()
        files.extend(
            self._filepath.with_suffix(suffix).as_posix()
            for suffix in [self._filepath.suffix + ".old"]
        )
        return files


class ValheimWorldSaveGame(ValheimSaveGame):
    def allFiles(self) -> list[str]:
        files = super().allFiles()
        files.extend(
            self._filepath.with_suffix(suffix).as_posix()
            for suffix in [".db", ".db.old"]
        )
        return files


class ValheimLocalSavegames(mobase.LocalSavegames):
    def __init__(self, myGameSaveDir):
        super().__init__()
        self._savesDir = myGameSaveDir.absolutePath()

    def mappings(self, profile_save_dir):
        return [
            mobase.Mapping(
                source=profile_save_dir.absolutePath(),
                destination=self._savesDir,
                is_directory=True,
                create_target=True,
            )
        ]

    def prepareProfile(self, profile):
        return profile.localSavesEnabled()


class ValheimGame(BasicGame):

    Name = "Valheim Support Plugin"
    Author = "Zash"
    Version = "1.1.1"

    GameName = "Valheim"
    GameShortName = "valheim"
    GameNexusId = 3667
    GameSteamId = [892970, 896660, 1223920]
    GameBinary = "valheim.exe"
    GameDataPath = ""
    GameSavesDirectory = r"%USERPROFILE%/AppData/LocalLow/IronGate/Valheim"

    forced_libraries = ["winhttp.dll"]

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = ValheimGameModDataChecker()
        self._featureMap[mobase.LocalSavegames] = ValheimLocalSavegames(
            self.savesDirectory()
        )
        self._overwrite_sync = OverwriteSync(organizer=self._organizer, game=self)
        self._register_event_handler()
        return True

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        return [
            mobase.ExecutableForcedLoadSetting(self.binaryName(), lib).withEnabled(True)
            for lib in self.forced_libraries
        ]

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        save_games = super().listSaves(folder)
        path = Path(folder.absolutePath())
        save_games.extend(ValheimSaveGame(f) for f in path.glob("characters/*.fch"))
        save_games.extend(ValheimWorldSaveGame(f) for f in path.glob("worlds/*.fwl"))
        return save_games

    def settings(self) -> list[mobase.PluginSetting]:
        settings = super().settings()
        settings.extend(
            [
                mobase.PluginSetting(
                    "sync_overwrite", "Sync overwrite with mods", True
                ),
                mobase.PluginSetting(
                    "search_overwrite_file_content",
                    "Search content of files in overwrite for matching mod",
                    True,
                ),
            ]
        )
        return settings

    def _register_event_handler(self):
        self._organizer.onUserInterfaceInitialized(lambda win: self._sync_overwrite())
        self._organizer.onFinishedRun(self._game_finished_event_handler)

    def _game_finished_event_handler(self, app_path: str, *args) -> None:
        """Sync overwrite folder with mods after game was closed."""
        if Path(app_path) == Path(
            self.gameDirectory().absolutePath(), self.binaryName()
        ):
            self._sync_overwrite()

    def _sync_overwrite(self) -> None:
        if self._organizer.pluginSetting(self.name(), "sync_overwrite") is not False:
            self._overwrite_sync.search_file_contents = (
                self._organizer.pluginSetting(
                    self.name(), "search_overwrite_file_content"
                )
                is not False
            )
            self._overwrite_sync.sync()
