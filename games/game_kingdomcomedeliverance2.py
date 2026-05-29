import os
import xml.etree.ElementTree as ET
from pathlib import Path

from PyQt6.QtCore import QDir, qInfo, qWarning

import mobase

from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_game import BasicGame


class KingdomComeDeliverance2Game(BasicGame):
    Name = "Kingdom Come: Deliverance 2 Support Plugin"
    Author = "TheForgotten69"
    Version = "1.0.0"

    GameName = "Kingdom Come: Deliverance II"
    GameShortName = "kingdomcomedeliverance2"
    GameNexusName = "kingdomcomedeliverance2"
    GameNexusId = 7286
    GameSteamId = [1771300]
    GameBinary = "bin/Win64MasterMasterSteamPGO/KingdomCome.exe"
    GameDataPath = "Mods"
    GameSaveExtension = "whs"
    GameDocumentsDirectory = "%GAME_PATH%"
    GameSavesDirectory = "%USERPROFILE%/Saved Games/kingdomcome2/saves"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(BasicModDataChecker(GlobPatterns(valid=["*"])))
        organizer.onAboutToRun(self._write_mod_order)
        return True

    @staticmethod
    def _get_mod_id(mod_path: Path) -> str | None:
        """Return the mod ID for a KCD2 mod.

        Checks mod.manifest for <modid> (preferred) or <name>, falling back
        to the game mod folder name (the subfolder inside the MO2 mod directory).
        """
        for manifest in mod_path.rglob("mod.manifest"):
            try:
                root = ET.parse(manifest).getroot()
                for tag in ("modid", "name"):
                    elem = root.find(f".//{tag}")
                    if elem is not None and elem.text and elem.text.strip():
                        return elem.text.strip()
            except ET.ParseError:
                qWarning(f"KCD2: failed to parse {manifest}")
            # Fall back to the folder that contains mod.manifest
            return manifest.parent.name
        # No manifest — use first subdirectory name (the game mod folder)
        for subdir in mod_path.iterdir():
            if subdir.is_dir():
                return subdir.name
        return None

    def _write_mod_order(self, app_path: str, wd: QDir, args: str) -> bool:
        if not self.isActive():
            return True

        modlist = self._organizer.modList()
        mods_path = Path(self._organizer.modsPath())
        mod_order_path = Path(self._organizer.overwritePath()) / "mod_order.txt"

        mod_ids: list[str] = []
        for mod_name in modlist.allModsByProfilePriority():
            if not (modlist.state(mod_name) & mobase.ModState.ACTIVE):
                continue
            mod_id = self._get_mod_id(mods_path / mod_name)
            if mod_id:
                qInfo(f"KCD2: mod '{mod_name}' -> id '{mod_id}'")
                mod_ids.append(mod_id)
            else:
                qWarning(f"KCD2: could not resolve id for mod '{mod_name}', skipping")

        if not mod_ids:
            mod_order_path.unlink(missing_ok=True)
            return True

        # MO2 priority 1 = top = highest priority. KCD2 is last-loaded-wins,
        # so highest priority must be last in the file.
        mod_ids.reverse()
        mod_order_path.parent.mkdir(parents=True, exist_ok=True)
        mod_order_path.write_text("\n".join(mod_ids))
        qInfo(f"KCD2: wrote mod_order.txt with {len(mod_ids)} mods: {mod_ids}")
        return True

    def iniFiles(self):
        return ["custom.cfg", "system.cfg", "user.cfg"]

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        for iniFile in self.iniFiles():
            iniPath = self.documentsDirectory().absoluteFilePath(iniFile)
            if not os.path.exists(iniPath):
                with open(iniPath, "w") as _:
                    pass

        modsPath = self.dataDirectory().absolutePath()
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)

        super().initializeProfile(directory, settings)
