from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QDir, QFileInfo

import mobase

from ..basic_features import BasicLocalSavegames, BasicModDataChecker, GlobPatterns
from ..basic_features.basic_save_game_info import BasicGameSaveGame
from ..basic_game import BasicGame


class GTA4ModDataChecker(BasicModDataChecker):
    """
    Normalize common GTA IV mod layouts for Complete Edition / classic IV.

    Typical destinations (game root as MO data path):
      - Ultimate ASI Loader / FusionFix: dinput8.dll (or xlive.dll), *.asi
      - Fusion Overloader content: update/
      - ScriptHookDotNet scripts: scripts/*.net.dll
      - IV-SDK .NET scripts: IVSDKDotNet/scripts/*.ivsdk.dll
      - IV Tweaker (1.0.7.0 / 1.0.8.0): modloader/
      - Direct replacements: common/, pc/, TLAD/, TBoGT/
    """

    def __init__(self, patterns: GlobPatterns | None = None):
        super().__init__(
            GlobPatterns(
                unfold=[
                    "Grand Theft Auto IV",
                    "GTA IV",
                    "GTAIV",
                    "GTA4",
                    "gta4",
                ],
                valid=[
                    # Content / overloader
                    "update",
                    "common",
                    "pc",
                    "TLAD",
                    "TBoGT",
                    "movies",
                    "modloader",
                    # Script frameworks
                    "scripts",
                    "IVSDKDotNet",
                    "plugins",
                    "plugins_disabled",
                    # Root ASI / loader files
                    "*.asi",
                    "dinput8.dll",
                    "xlive.dll",
                    "dsound.dll",
                    # FusionFix / DXVK / graphics helpers
                    "d3d9.dll",
                    "d3d10.dll",
                    "d3d11.dll",
                    "dxgi.dll",
                    "vulkan.dll",
                    "bass.dll",
                    "ScriptHook.dll",
                    "ScriptHookDotNet.dll",
                    "ScriptHookDotNet.asi",
                    "AdvancedHook.dll",
                    "AdvancedHookInit.asi",
                    "aCompleteEditionHook.asi",
                    "ClrHook.dll",
                    # Common companion / config files
                    "*.ini",
                    "*.cfg",
                    "*.xml",
                    "*.dll",
                ],
                delete=[
                    "*.md",
                    "*.txt",
                    "*.pdf",
                    "*.url",
                    "*.jpg",
                    "*.jpeg",
                    "*.png",
                    "*.gif",
                    "*.webp",
                    "readme*",
                    "read me*",
                    "License*",
                    "LICENSE*",
                    "fomod",
                ],
                move={
                    # ScriptHookDotNet / IV-SDK scripts often ship loose
                    "*.net.dll": "scripts/",
                    "*.ivsdk.dll": "IVSDKDotNet/scripts/",
                    # Loose IMG packs for Fusion Overloader
                    "*.img": "update/",
                },
            ).merge(patterns or GlobPatterns())
        )


class GTA4Game(BasicGame):
    Name = "Grand Theft Auto IV Support Plugin"
    Author = "vmRyn"
    Version = "1.0.0"
    Description = (
        "Adds support for Grand Theft Auto IV / The Complete Edition "
        "(ASI loaders, FusionFix/Overloader, ScriptHookDotNet, IV-SDK .NET)."
    )

    GameName = "Grand Theft Auto IV"
    GameShortName = "gta4"
    GameNexusName = "gta4"
    GameNexusId = 253
    GameSteamId = [12210, 12220]  # IV Complete Edition; legacy EFLC
    GameBinary = "GTAIV.exe"
    GameDataPath = ""
    GameDocumentsDirectory = (
        "%USERPROFILE%/AppData/Local/Rockstar Games/GTA IV/Settings"
    )
    GameSavesDirectory = "%DOCUMENTS%/Rockstar Games/GTA IV/Profiles"
    GameIniFiles = ["SETTINGS.CFG"]
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Grand-Theft-Auto-IV"
    )

    # Ultimate ASI Loader / FusionFix. xlive.dll is the GFWL-removal rename of
    # dinput8.dll used on older patches; force both so VFS injects them.
    _forced_libraries = ["dinput8.dll", "xlive.dll"]

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(GTA4ModDataChecker())
        # Older MO2 builds take QDir; current basic_games takes IPluginGame.
        try:
            local_saves = BasicLocalSavegames(self)
        except AttributeError:
            local_saves = BasicLocalSavegames(self.savesDirectory())
        self._register_feature(local_saves)
        return True

    def looksValid(self, directory: QDir) -> bool:
        # Complete Edition and classic IV both ship GTAIV.exe. Older Steam
        # installs may also have LaunchGTAIV.exe as a secondary launcher.
        return directory.exists(self.binaryName()) or directory.exists(
            "LaunchGTAIV.exe"
        )

    def executables(self) -> list[mobase.ExecutableInfo]:
        game_dir = self.gameDirectory()
        execs = [
            mobase.ExecutableInfo(
                "Grand Theft Auto IV",
                QFileInfo(game_dir.absoluteFilePath(self.binaryName())),
            ),
        ]
        # Legacy Steam launcher (pre–Complete Edition / some downgrades)
        launch = game_dir.absoluteFilePath("LaunchGTAIV.exe")
        if QFileInfo(launch).exists():
            execs.append(
                mobase.ExecutableInfo(
                    "Launch GTA IV",
                    QFileInfo(launch),
                )
            )
        return execs

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        loads: list[mobase.ExecutableForcedLoadSetting] = []
        for exe in self.executables():
            exe_name = exe.binary().fileName()
            for lib in self._forced_libraries:
                loads.append(
                    mobase.ExecutableForcedLoadSetting(exe_name, lib).withEnabled(True)
                )
        return loads

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        """
        Complete Edition: Documents/Rockstar Games/GTA IV/Profiles/<id>/SGTA4XX
        (no file extension). Also accept older extensionless/alternate layouts
        under the configured saves directory.
        """
        root = Path(folder.absolutePath())
        if not root.exists():
            return []

        saves: list[mobase.ISaveGame] = []
        seen: set[Path] = set()
        for pattern in ("**/SGTA4*", "**/SGTA4*.*", "**/savegames/**/*"):
            for path in root.glob(pattern):
                if not path.is_file():
                    continue
                # Skip obvious non-save profile clutter
                name = path.name.casefold()
                if name in {
                    "profilesettings",
                    "controlmap.dat",
                    "cloudsavedata.dat",
                }:
                    continue
                if path.suffix.casefold() in {".dat"} and not name.startswith("sgta"):
                    continue
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                saves.append(BasicGameSaveGame(path))
        return saves
