import json
import re
import shutil
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeVar

import mobase
from PyQt6.QtCore import QDateTime, QDir, qInfo

from ..basic_features import BasicLocalSavegames, BasicModDataChecker, GlobPatterns
from ..basic_features.basic_save_game_info import (
    BasicGameSaveGame,
    BasicGameSaveGameInfo,
    format_date,
)
from ..basic_features.utils import is_directory
from ..basic_game import BasicGame


class CyberpunkModDataChecker(BasicModDataChecker):
    def __init__(self):
        super().__init__(
            GlobPatterns(
                valid=[
                    "archive",
                    # redscript
                    "engine",
                    "r6",
                    "mods",  # RedMod
                    "red4ext",  # red4ext/RED4ext.dll is moved to root in .fix()
                    "bin",  # CET etc. gets handled below
                    "root",  # RootBuilder: hardlink / copy to game root
                ],
                move={
                    # archive and ArchiveXL
                    "*.archive": "archive/pc/mod/",
                    "*.xl": "archive/pc/mod/",
                },
            )
        )

    _extra_files_to_move = {
        # Red4ext: only .dll files
        "red4ext/RED4ext.dll": "root/red4ext/",
        "bin/x64/winmm.dll": "root/bin/x64/",
        # CET: all files, folder gets handled in .fix()
        "bin/x64/version.dll": "root/bin/x64/",
        "bin/x64/global.ini": "root/bin/x64/",
        "bin/x64/plugins/cyber_engine_tweaks.asi": "root/bin/x64/plugins/",
    }
    """Some frameworks need to be copied or hard linked to root. Use / as sep!"""
    _ignore_pattern = re.compile(r"licenses?$", re.I)

    _cet_path = "bin/x64/plugins/cyber_engine_tweaks/"

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        # fix: single root folders get traversed by Simple Installer
        parent = filetree.parent()
        if parent is not None and self.dataLooksValid(parent) is self.FIXABLE:
            return self.FIXABLE
        if (status := super().dataLooksValid(filetree)) is not self.INVALID:
            match self._check_bin_folder(filetree):
                case self.INVALID:
                    return self.INVALID
                case self.FIXABLE:
                    status = self.FIXABLE
                case _:
                    pass  # valid = keep status
            # Check extra fixes
            if any(filetree.exists(p) for p in self._extra_files_to_move):
                status = self.FIXABLE
        return status

    def _check_bin_folder(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        """Only Red4ext and CET are supported in bin folder."""
        bin_folder = filetree.find("bin/x64")
        if not bin_folder:
            return self.VALID
        elif not is_directory(bin_folder):
            return self.INVALID
        status = self.VALID
        cet_path = self._cet_path.rstrip("/\\")
        for entry in bin_folder:
            entry_name = entry.name()
            if self._ignore_pattern.match(entry_name):
                continue
            elif f"bin/x64/{entry_name}" in self._extra_files_to_move:
                status = self.FIXABLE
            elif entry_name == "plugins" and is_directory(entry):
                for plugin in entry:
                    plugin_path = f"bin/x64/plugins/{plugin.name()}"
                    if plugin_path == cet_path:
                        if not is_directory(plugin):
                            return self.INVALID
                        if not (len(plugin) == 1 and plugin.exists("mods")):
                            status = self.FIXABLE  # CET framework: fix
                    elif plugin_path in self._extra_files_to_move:
                        status = self.FIXABLE
                    else:
                        return self.INVALID  # unknown plugin
            else:
                return self.INVALID  # unknown entry
        return status

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        if filetree := super().fix(filetree):
            for source, target in self._extra_files_to_move.items():
                if file := filetree.find(source):
                    parent = file.parent()
                    filetree.move(file, target)
                    clear_empty_folder(parent)
            self._fix_cet_framework(filetree)
        return filetree

    def _fix_cet_framework(self, filetree: mobase.IFileTree):
        """Move CET framework to `root/`, except for `mods`.
        Only CET >= v1.27.0 (Patch 2.01) works with USVFS.

        See: https://github.com/maximegmd/CyberEngineTweaks/pull/877
        """
        if cet_folder := filetree.find(
            self._cet_path, mobase.FileTreeEntry.FileTypes.DIRECTORY
        ):
            assert is_directory(cet_folder)
            root_cet_path = f"root/{self._cet_path}"
            if not cet_folder.exists("mods"):
                parent = cet_folder.parent()
                filetree.move(cet_folder, root_cet_path.rstrip("/\\"))
            else:
                parent = cet_folder
                for entry in list(cet_folder):
                    if entry.name() != "mods":
                        filetree.move(entry, root_cet_path)
            clear_empty_folder(parent)


def clear_empty_folder(filetree: mobase.IFileTree | None):
    if filetree is None:
        return
    while not filetree:
        parent = filetree.parent()
        filetree.detach()
        if parent is None:
            break
        filetree = parent


def time_from_seconds(s: int | float) -> str:
    m, s = divmod(int(s), 60)
    h, m = divmod(int(m), 60)
    return f"{h:02}:{m:02}:{s:02}"


def parse_cyberpunk_save_metadata(save_path: Path, save: mobase.ISaveGame):
    metadata_file = save_path / "metadata.9.json"
    try:
        with open(metadata_file) as file:
            meta_data = json.load(file)["Data"]["metadata"]
            name = meta_data["name"]
            if name != (save_name := save.getName()):
                name = f"{save_name}  ({name})"
            return {
                "Name": name,
                "Date": format_date(meta_data["timestampString"], "hh:mm:ss, d.M.yyyy"),
                "Play Time": time_from_seconds(meta_data["playthroughTime"]),
                "Quest": meta_data["trackedQuestEntry"],
                "Level": int(meta_data["level"]),
                "Street Cred": int(meta_data["streetCred"]),
                "Life Path": meta_data["lifePath"],
                "Difficulty": meta_data["difficulty"],
                "Gender": f'{meta_data["bodyGender"]} / {meta_data["brainGender"]}',
                "Game version": meta_data["buildPatch"],
            }
    except (FileNotFoundError, json.JSONDecodeError):
        return None


class CyberpunkSaveGame(BasicGameSaveGame):
    _name_file = "NamedSave.txt"  # from mod: Named Saves

    def __init__(self, filepath: Path):
        super().__init__(filepath)
        try:  # Custom name from Named Saves
            with open(filepath / self._name_file) as file:
                self._name = file.readline()
        except FileNotFoundError:
            self._name = ""

    def getName(self) -> str:
        return self._name or super().getName()

    def getCreationTime(self) -> QDateTime:
        return QDateTime.fromSecsSinceEpoch(
            int((self._filepath / "sav.dat").stat().st_mtime)
        )


@dataclass
class ModListFile:
    list_path: Path
    mod_search_pattern: str


_MOD_TYPE = TypeVar("_MOD_TYPE")


class ModListFileManager(dict[_MOD_TYPE, ModListFile]):
    """Manages modlist files for specific mod types."""

    def __init__(self, organizer: mobase.IOrganizer, **kwargs: ModListFile) -> None:
        self._organizer = organizer
        super().__init__(**kwargs)

    def update_modlist(
        self, mod_type: _MOD_TYPE, mod_files: list[str] | None = None
    ) -> tuple[Path, list[str], list[str]]:
        """
        Updates the mod list file for `mod_type` with the current load order.
        Removes the file if it is not needed.

        Args:
            mod_type: Which modlist to update.
            mod_files (optional): By default mod files in order of mod priority.

        Returns:
            `(modlist_path, new_mod_list, old_mod_list)`
        """
        if mod_files is None:
            mod_files = list(self.modfile_names(mod_type))
        modlist_path = self.absolute_modlist_path(mod_type)
        old_modlist = (
            modlist_path.read_text().splitlines() if modlist_path.exists() else []
        )
        if not mod_files or len(mod_files) == 1:
            # No load order required
            if old_modlist:
                qInfo(f"Removing {mod_type} load order {modlist_path}")
                modlist_path.unlink()
            return modlist_path, [], old_modlist
        else:
            qInfo(f'Updating {mod_type} load order "{modlist_path}" with: {mod_files}')
            modlist_path.parent.mkdir(parents=True, exist_ok=True)
            modlist_path.write_text("\n".join(mod_files))
            return modlist_path, mod_files, old_modlist

    def absolute_modlist_path(self, mod_type: _MOD_TYPE) -> Path:
        modlist_path = self[mod_type].list_path
        if not modlist_path.is_absolute():
            existing = self._organizer.findFiles(modlist_path.parent, modlist_path.name)
            overwrite = self._organizer.overwritePath()
            modlist_path = (
                Path(existing[0]) if (existing) else Path(overwrite, modlist_path)
            )
        return modlist_path

    def modfile_names(self, mod_type: _MOD_TYPE) -> Iterable[str]:
        """Get all files from the `mod_type` in load order."""
        yield from (file.name for file in self.modfiles(mod_type))

    def modfiles(self, mod_type: _MOD_TYPE) -> Iterable[Path]:
        """Get all files from the `mod_type` in load order."""
        mod_search_pattern = self[mod_type].mod_search_pattern
        for mod_path in self.active_mod_paths():
            yield from mod_path.glob(mod_search_pattern)

    def active_mod_paths(self) -> Iterable[Path]:
        """Yield the path to active mods in load order."""
        mods_path = Path(self._organizer.modsPath())
        modlist = self._organizer.modList()
        for mod in modlist.allModsByProfilePriority():
            if modlist.state(mod) & mobase.ModState.ACTIVE:
                yield mods_path / mod


class Cyberpunk2077Game(BasicGame):
    Name = "Cyberpunk 2077 Support Plugin"
    Author = "6788, Zash"
    Version = "2.0.0"

    GameName = "Cyberpunk 2077"
    GameShortName = "cyberpunk2077"
    GameBinary = "bin/x64/Cyberpunk2077.exe"
    GameLauncher = "REDprelauncher.exe"
    GameDataPath = "%GAME_PATH%"
    GameDocumentsDirectory = "%USERPROFILE%/AppData/Local/CD Projekt Red/Cyberpunk 2077"
    GameSavesDirectory = "%USERPROFILE%/Saved Games/CD Projekt Red/Cyberpunk 2077"
    GameSaveExtension = "dat"
    GameSteamId = 1091500
    GameGogId = 1423049311
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Cyberpunk-2077"
    )

    _redmod_binary = Path("tools/redmod/bin/redMod.exe")
    _redmod_deploy_path = Path("r6/cache/modded/")
    _redmod_deploy_args = "deploy -reportProgress"
    """Deploy arguments for `redmod.exe`, -modlist=... is added."""

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._featureMap[mobase.LocalSavegames] = BasicLocalSavegames(
            self.savesDirectory()
        )
        self._featureMap[mobase.SaveGameInfo] = BasicGameSaveGameInfo(
            lambda p: Path(p or "", "screenshot.png"),
            parse_cyberpunk_save_metadata,
        )
        self._featureMap[mobase.ModDataChecker] = CyberpunkModDataChecker()

        self._modlist_files = ModListFileManager[Literal["archive", "redmod"]](
            organizer,
            archive=ModListFile(
                Path("archive/pc/mod/modlist.txt"),
                "archive/pc/mod/*",
            ),
            redmod=ModListFile(
                Path(self._redmod_deploy_path, "MO_REDmod_load_order.txt"),
                "mods/*/",
            ),
        )

        organizer.onAboutToRun(self._onAboutToRun)
        return True

    def iniFiles(self):
        return ["UserSettings.json"]

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        ext = self._mappings.savegameExtension.get()
        return [
            CyberpunkSaveGame(path.parent)
            for path in Path(folder.absolutePath()).glob(f"**/*.{ext}")
        ]

    def settings(self) -> list[mobase.PluginSetting]:
        return [
            mobase.PluginSetting(
                "skipStartScreen",
                'Skips the "Breaching..." start screen on game launch',
                True,
            ),
            mobase.PluginSetting(
                "enforce_archive_load_order",
                (
                    "Enforce the current load order via"
                    " <code>archive/pc/mod/modlist.txt</code>"
                ),
                True,
            ),
            mobase.PluginSetting(
                "enforce_redmod_load_order",
                "Enforce the current load order on redmod deployment",
                True,
            ),
            mobase.PluginSetting(
                "auto_deploy_redmod",
                "Deploy redmod before game launch if necessary",
                True,
            ),
        ]

    def _get_setting(self, key: str) -> mobase.MoVariant:
        return self._organizer.pluginSetting(self.name(), key)

    def executables(self) -> list[mobase.ExecutableInfo]:
        game_name = self.gameName()
        game_dir = self.gameDirectory()
        bin_path = game_dir.absoluteFilePath(self.binaryName())
        skip_start_screen = (
            " -skipStartScreen" if self._get_setting("skipStartScreen") else ""
        )
        return [
            mobase.ExecutableInfo(
                f"{game_name}",
                bin_path,
            ).withArgument(f"--launcher-skip -modded{skip_start_screen}"),
            # Deploy REDmods
            mobase.ExecutableInfo(
                "Manually deploy REDmod",
                self._get_redmod_binary(),
            ).withArgument("deploy -reportProgress -force %modlist%"),
            # Launcher
            mobase.ExecutableInfo(
                "REDprelauncher",
                game_dir.absoluteFilePath(self.getLauncherName()),
            ).withArgument(f"{skip_start_screen}"),
        ]

    def _get_redmod_binary(self) -> Path:
        """Absolute path to redmod binary"""
        return Path(self.gameDirectory().absolutePath(), self._redmod_binary)

    def _onAboutToRun(self, app_path_str: str, wd: QDir, args: str) -> bool:
        if not self.isActive():
            return True
        app_path = Path(app_path_str)
        if app_path == self._get_redmod_binary():
            if m := re.search(r"%modlist%", args, re.I):
                # Manual deployment: replace %modlist% variable
                (
                    modlist_path,
                    modlist,
                    _,
                ) = self._modlist_files.update_modlist("redmod")
                modlist_param = f'-modlist="{modlist_path}"' if modlist else ""
                args = f"{args[:m.start()]}{modlist_param}{args[m.end():]}"
                qInfo(f"Manual modlist deployment: replacing {m[0]}, new args = {args}")
                self._organizer.waitForApplication(
                    self._organizer.startApplication(app_path_str, [args], wd), False
                )
                return False
            return True  # No recursive call
        if (
            self._get_setting("auto_deploy_redmod")
            and app_path == Path(self.gameDirectory().absolutePath(), self.binaryName())
            and "-modded" in args
            and not self._deploy_redmod()
        ):
            return False
        self._map_cache_files()
        if self._get_setting("enforce_archive_load_order"):
            self._modlist_files.update_modlist("archive")
        return True

    def _deploy_redmod(self) -> bool:
        """Deploys redmod. Clears deployed files if no redmods are active.
        Recreates deployed files to force load order when necessary.

        Returns:
            False failed deployment, else True
        """
        # Add REDmod load order if none is specified
        redmod_list = list(self._modlist_files.modfile_names("redmod"))
        if not redmod_list:
            qInfo("Cleaning up redmod deployed files")
            self._clean_deployed_redmod()
            return True
        args = self._redmod_deploy_args
        if self._get_setting("enforce_redmod_load_order"):
            modlist_path, _, old_redmods = self._modlist_files.update_modlist(
                "redmod", redmod_list
            )
            if (
                Counter(redmod_list) == Counter(old_redmods)
                and not redmod_list == old_redmods
            ):
                # Only load order changed: recreate redmod deploys
                # Fix for redmod not detecting change of load order.
                # Faster than -force https://github.com/E1337Kat/cyberpunk2077_ext_redux/issues/297  # noqa: E501
                qInfo("Redmod order changed, recreate deployed files")
                self._clean_deployed_redmod(modlist_path)
            qInfo(f"Deploying redmod with modlist: {modlist_path}")
            args += f' -modlist="{modlist_path}"'
        else:
            qInfo("Deploying redmod")
        redmod_binary = self._get_redmod_binary()
        return self._organizer.waitForApplication(
            self._organizer.startApplication(
                redmod_binary, [args], redmod_binary.parent
            ),
            False,
        )[0]

    def _clean_deployed_redmod(self, modlist_path: Path | None = None):
        """Delete all files from `_redmod_deploy_path` except for `modlist_path`."""
        for file in self._organizer.findFiles(self._redmod_deploy_path, "*"):
            file_path = Path(file)
            if modlist_path is None or file_path != modlist_path:
                file_path.unlink()

    def _map_cache_files(self):
        """
        Copy cache files (`final.redscript` etc.) to overwrite to catch
        overwritten game files.
        """
        data_path = Path(self.dataDirectory().absolutePath())
        if unmapped_cache_files := self._unmapped_cache_files(data_path):
            qInfo('Copying "r6/cache/*" to overwrite (to catch file overwrites)')
            overwrite_path = Path(self._organizer.overwritePath())
            for file in unmapped_cache_files:
                dst = overwrite_path / file.relative_to(data_path)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, dst)

    def _unmapped_cache_files(self, data_path: Path) -> list[Path]:
        return [
            path
            for file in self._organizer.findFiles("r6/cache", "*")
            if (path := Path(file).absolute()).is_relative_to(data_path)
        ]
