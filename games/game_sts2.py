import json
import re
from pathlib import Path

from PyQt6.QtCore import QDir, QFileInfo, qInfo, qWarning

import mobase

from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_features.basic_save_game_info import BasicGameSaveGame
from ..basic_game import BasicGame
from ..steam_utils import find_steam_path


class SlayTheSpire2ModDataChecker(BasicModDataChecker):
    def __init__(self):
        super().__init__(
            GlobPatterns(
                valid=[
                    "*.pck",
                    "*.dll",
                    "*.json",
                ],
                move={
                    "*/*.pck": "",
                    "*/*.dll": "",
                    "*/*.json": "",
                },
            )
        )


class SlayTheSpire2Game(BasicGame):
    Name = "Slay the Spire 2 Support Plugin"
    Author = "Azlle"
    Version = "1.1.0"

    GameName = "Slay the Spire 2"
    GameShortName = "slaythespire2"
    GameNexusName = "slaythespire2"
    GameNexusId = 8916
    GameSteamId = 2868840
    GameBinary = "SlayTheSpire2.exe"
    GameDataPath = "mods"
    GameDocumentsDirectory = "%USERPROFILE%/AppData/Roaming/SlayTheSpire2"

    _last_save_dir: str = ""

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(SlayTheSpire2ModDataChecker())
        organizer.modList().onModInstalled(self._on_mod_installed)
        return True

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        mods_path = Path(self.dataDirectory().absolutePath())
        if not mods_path.exists():
            qInfo(f"Creating mods directory: {mods_path}")
            mods_path.mkdir()
        super().initializeProfile(directory, settings)

    def _on_mod_installed(self, mod: mobase.IModInterface):
        mod_name = mod.name()
        self._organizer.onNextRefresh(
            lambda: self._apply_version(self._organizer.modList().getMod(mod_name)), True
        )

    def _apply_version(self, mod: mobase.IModInterface | None):
        if mod is None:
            return
        mod_path = Path(mod.absolutePath())
        for json_file in mod_path.glob("*.json"):
            try:
                with open(json_file, encoding="utf-8-sig") as f:
                    data = json.load(f)
                    if version := data.get("version"):
                        version = version.lstrip("v")
                        meta_ini = mod_path / "meta.ini"
                        raw = meta_ini.read_bytes()
                        raw = re.sub(rb"^\s*version\s*=\s*[^\r\n]*", f"version={version}".encode(), raw, flags=re.MULTILINE)
                        meta_ini.write_bytes(raw)
                        qInfo(f"Set version of {mod_path.name} to {version} using {json_file.name}")
                        self._organizer.modDataChanged(mod)
                        break
            except (json.JSONDecodeError, OSError) as e:
                qWarning(f"Failed to apply version for {mod_path.name} via {json_file.name}: {e}")
                continue

    def savesDirectory(self) -> QDir:
        steam_dir = Path(self.documentsDirectory().absolutePath()) / "steam"
        candidates = []
        is_fallback = False
        steam_path = find_steam_path()
        if steam_path is not None:
            userdata = steam_path / "userdata"
            if userdata.exists():
                candidates = [
                    child / "2868840" / "remote"
                    for child in userdata.iterdir()
                    if child.is_dir() and (child / "2868840" / "remote").exists()
                ]
        if not candidates:
            is_fallback = True
            if steam_dir.exists():
                candidates = [child for child in steam_dir.iterdir() if child.is_dir()]
        if candidates:
            save_dir = max(candidates, key=lambda p: p.stat().st_mtime)
            if (s := str(save_dir)) != self._last_save_dir:
                status = "not found, using AppData" if is_fallback else "found"
                qInfo(f"Steam save directory {status}: {save_dir}")
                self.__class__._last_save_dir = s
            return QDir(s)
        return QDir(str(steam_dir))

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        base = Path(folder.absolutePath())
        return [
            BasicGameSaveGame(save)
            for save in base.rglob("*")
            if save.is_file() and save.suffix in (".save", ".run", ".backup")
        ]

    def executables(self):
        return [
            mobase.ExecutableInfo(
                self.GameName,
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
            mobase.ExecutableInfo(
                f"{self.GameName} (OpenGL)",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ).withArgument("--rendering-driver opengl3"),
        ]
