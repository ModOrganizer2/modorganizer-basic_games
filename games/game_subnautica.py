from __future__ import annotations

import os
from collections.abc import Iterable
from enum import Enum
from pathlib import Path

import mobase
from PyQt6.QtCore import QDir, qWarning

from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_features.basic_save_game_info import (
    BasicGameSaveGame,
    BasicGameSaveGameInfo,
)
from ..basic_game import BasicGame


class SubnauticaModDataChecker(BasicModDataChecker):
    def __init__(self, patterns: GlobPatterns = GlobPatterns()):
        super().__init__(
            GlobPatterns(
                unfold=["BepInExPack_Subnautica"],
                valid=["winhttp.dll", "doorstop_config.ini", "BepInEx", "QMods"],
                delete=[
                    "*.txt",
                    "*.md",
                    "icon.png",
                    "license",
                    "manifest.json",
                ],
                move={"plugins": "BepInEx/", "patchers": "BepInEx/", "*": "QMods/"},
            ).merge(patterns),
        )


class SubnauticaGame(BasicGame, mobase.IPluginFileMapper):
    Name = "Subnautica Support Plugin"
    Author = "dekart811, Zash"
    Version = "2.1.1"

    GameName = "Subnautica"
    GameShortName = "subnautica"
    GameNexusName = "subnautica"
    GameSteamId = 264710
    GameEpicId = "Jaguar"
    GameBinary = "Subnautica.exe"
    GameDataPath = "_ROOT"  # Custom mappings to actual root folders below.
    GameDocumentsDirectory = r"%GAME_PATH%"
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Subnautica"
    )
    GameSavesDirectory = r"%GAME_PATH%\SNAppData\SavedGames"

    _game_extra_save_paths = [
        r"%USERPROFILE%\Appdata\LocalLow\Unknown Worlds"
        r"\Subnautica\Subnautica\SavedGames"
    ]

    _forced_libraries = ["winhttp.dll"]

    _root_blacklist = {GameDataPath.casefold()}

    class MapType(Enum):
        FILE = 0
        FOLDER = 1

    _root_extra_overwrites: dict[str, MapType] = {
        "qmodmanager_log-Subnautica.txt": MapType.FILE,
        "qmodmanager-config.json": MapType.FILE,
        "BepInEx_Shim_Backup": MapType.FOLDER,
    }
    """Extra files & folders created in game root by mods / BepInEx after game launch,
    but not included in the mod archives.
    """

    def __init__(self):
        super().__init__()
        mobase.IPluginFileMapper.__init__(self)

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = SubnauticaModDataChecker()
        self._featureMap[mobase.SaveGameInfo] = BasicGameSaveGameInfo(
            lambda s: Path(s or "", "screenshot.jpg")
        )
        return True

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        return [
            BasicGameSaveGame(folder)
            for save_path in (
                folder.absolutePath(),
                *(os.path.expandvars(p) for p in self._game_extra_save_paths),
            )
            for folder in Path(save_path).glob("slot*")
        ]

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        return [
            mobase.ExecutableForcedLoadSetting(self.binaryName(), lib).withEnabled(True)
            for lib in self._forced_libraries
        ]

    def mappings(self) -> list[mobase.Mapping]:
        game = self._organizer.managedGame()
        game_path = Path(game.gameDirectory().absolutePath())
        overwrite_path = Path(self._organizer.overwritePath())

        return [
            *(
                # Extra overwrites
                self._overwrite_mapping(
                    overwrite_path / name,
                    dest,
                    is_dir=(map_type is self.MapType.FOLDER),
                )
                for name, map_type in self._root_extra_overwrites.items()
                if not (dest := game_path / name).exists()
            ),
            *self._root_mappings(game_path, overwrite_path),
        ]

    def _root_mappings(
        self, game_path: Path, overwrite_path: Path
    ) -> Iterable[mobase.Mapping]:
        for mod_path in self._active_mod_paths():
            mod_name = mod_path.name

            for child in mod_path.iterdir():
                # Check blacklist
                if child.name.casefold() in self._root_blacklist:
                    qWarning(f"Skipping {child.name} ({mod_name})")
                    continue
                destination = game_path / child.name
                # Check existing
                if destination.exists():
                    qWarning(
                        f"Overwriting of existing game files/folders is not supported! "
                        f"{destination.as_posix()} ({mod_name})"
                    )
                    continue
                # Mapping: mod -> root
                yield mobase.Mapping(
                    source=str(child),
                    destination=str(destination),
                    is_directory=child.is_dir(),
                    create_target=False,
                )
                if child.is_dir():
                    # Mapping: overwrite <-> root
                    yield self._overwrite_mapping(
                        overwrite_path / child.name, destination, is_dir=True
                    )

    def _active_mod_paths(self) -> Iterable[Path]:
        mods_parent_path = Path(self._organizer.modsPath())
        modlist = self._organizer.modList().allModsByProfilePriority()
        for mod in modlist:
            if self._organizer.modList().state(mod) & mobase.ModState.ACTIVE:
                yield mods_parent_path / mod

    def _overwrite_mapping(
        self, overwrite_source: Path, destination: Path, is_dir: bool
    ) -> mobase.Mapping:
        """Mapping: overwrite <-> root"""
        if is_dir:
            # Root folders in overwrite need to exits.
            overwrite_source.mkdir(parents=True, exist_ok=True)
        return mobase.Mapping(
            str(overwrite_source),
            str(destination),
            is_dir,
            create_target=True,
        )
