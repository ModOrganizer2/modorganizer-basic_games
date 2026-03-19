import uuid
import re
from pathlib import Path
from typing import Iterable

import mobase
from PyQt6.QtCore import QDir

from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_game import BasicGame


class MonsterHunterWildsModDataChecker(BasicModDataChecker):
    def __init__(self):
        super().__init__(
            GlobPatterns(
                valid=[
                    "dinput8.dll",
                    "*.pak",
                    "natives",
                    "reframework",
                ],
                delete=[
                    "modinfo.ini",
                    "*.png",
                    "*.jpg",
                    "*.jpeg",
                    "*.webp",
                ],
            )
        )


class MonsterHunterWildsGame(BasicGame):
    Name = "Monster Hunter: Wilds Support Plugin"
    Author = "Yashirow"
    Version = "1.0.1"

    GameName = "Monster Hunter: Wilds"
    GameShortName = "monsterhunterwilds"
    GameBinary = "MonsterHunterWilds.exe"
    GameDataPath = "%GAME_PATH%"
    GameSaveExtension = "bin"
    GameNexusId = 6993
    GameSteamId = 2246340

    _PAK_PATTERN = re.compile(
        r"re_chunk_000\.pak\.sub_000\.pak\.patch_(\d+)\.pak$", re.IGNORECASE
    )

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(MonsterHunterWildsModDataChecker())
        organizer.onAboutToRun(self._onAboutToRun)
        return True

    def _game_root(self) -> Path:
        return Path(self.gameDirectory().absolutePath())

    def _active_mod_paths(self) -> Iterable[Path]:
        mods_parent_path = Path(self._organizer.modsPath())
        modlist = self._organizer.modList().allModsByProfilePriority()
        for mod_name in modlist:
            if self._organizer.modList().state(mod_name) & mobase.ModState.ACTIVE:
                yield mods_parent_path / mod_name

    def _overwrite_path(self) -> Path:
        return Path(self._organizer.overwritePath())

    def _next_patch_number(self) -> int:
        max_patch = -1
        for pak_path in self._game_root().glob("*.pak"):
            match = self._PAK_PATTERN.fullmatch(pak_path.name)
            if match:
                max_patch = max(max_patch, int(match.group(1)))
        return max_patch + 1

    def _root_paks(self, root_path: Path) -> list[Path]:
        return sorted(
            [
                child
                for child in root_path.iterdir()
                if child.is_file() and child.suffix.lower() == ".pak"
            ],
            key=lambda path: path.name.casefold(),
        )

    def _rename_paks(self):
        pak_files: list[tuple[Path, Path]] = []
        next_patch = self._next_patch_number()

        for mod_path in self._active_mod_paths():
            for pak_path in self._root_paks(mod_path):
                target_name = (
                    f"re_chunk_000.pak.sub_000.pak.patch_{next_patch:03d}.pak"
                )
                pak_files.append((pak_path, mod_path / target_name))
                next_patch += 1

        overwrite_path = self._overwrite_path()
        if overwrite_path.exists():
            for pak_path in self._root_paks(overwrite_path):
                target_name = (
                    f"re_chunk_000.pak.sub_000.pak.patch_{next_patch:03d}.pak"
                )
                pak_files.append((pak_path, overwrite_path / target_name))
                next_patch += 1

        temporary_paths: list[tuple[Path, Path]] = []
        for source_path, target_path in pak_files:
            if source_path == target_path:
                continue
            temp_path = source_path.with_name(
                f"{source_path.stem}.{uuid.uuid4().hex}.tmp{source_path.suffix}"
            )
            source_path.rename(temp_path)
            temporary_paths.append((temp_path, target_path))

        for temp_path, target_path in temporary_paths:
            temp_path.rename(target_path)

    def _onAboutToRun(self, app_path_str: str, wd: QDir, args: str) -> bool:
        if Path(app_path_str) == self._game_root() / self.binaryName():
            self._rename_paks()
        return True


