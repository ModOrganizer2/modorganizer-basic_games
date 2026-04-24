import json
import re
from pathlib import Path

from PyQt6.QtCore import QDir, QFileInfo, qInfo, qWarning

import mobase

from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_features.basic_save_game_info import BasicGameSaveGame
from ..basic_game import BasicGame


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
    Version = "1.0.1"

    GameName = "Slay the Spire 2"
    GameShortName = "slaythespire2"
    GameNexusName = "slaythespire2"
    GameNexusId = 8916
    GameSteamId = 2868840
    GameBinary = "SlayTheSpire2.exe"
    GameDataPath = "mods"
    GameDocumentsDirectory = "%USERPROFILE%/AppData/Roaming/SlayTheSpire2"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(SlayTheSpire2ModDataChecker())
        organizer.modList().onModInstalled(self._on_mod_installed)
        return True

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        mods_path = Path(self.dataDirectory().absolutePath())
        mods_path.mkdir(exist_ok=True)
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
        docs = QDir(self.documentsDirectory())
        steam_dir = Path(docs.absoluteFilePath("steam"))
        if steam_dir.exists():
            entries = [e for e in steam_dir.iterdir() if e.is_dir()]
            if entries:
                return QDir(str(entries[0]))
        return QDir(str(steam_dir))

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        base = Path(folder.absolutePath())
        return [
            BasicGameSaveGame(save)
            for save in base.rglob("*")
            if save.is_file() and save.suffix in (".save", ".run")
        ]

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Slay the Spire 2",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
            mobase.ExecutableInfo(
                "Slay the Spire 2 (OpenGL)",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ).withArgument("--rendering-driver opengl3"),
        ]
