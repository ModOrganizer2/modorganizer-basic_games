from __future__ import annotations

import mobase

from ..basic_features.basic_mod_data_checker import BasicModDataChecker, FilePatterns
from ..basic_game import BasicGame

subnautica_file_patterns = FilePatterns(
    set_as_root={"BepInExPack_Subnautica"},
    valid={"winhttp.dll", "doorstop_config.ini", "BepInEx", "QMods"},
    delete={
        "*.txt",
        "*.md",
        "icon.png",
        "license",
        "manifest.json",
    },
    move={"plugins": "BepInEx/", "patchers": "BepInEx/", "*": "QMods/"},
)


class SubnauticaGame(BasicGame):

    Name = "Subnautica Support Plugin"
    Author = "dekart811, Zash"
    Version = "2.0"

    GameName = "Subnautica"
    GameShortName = "subnautica"
    GameNexusName = "subnautica"
    GameSteamId = 264710
    GameBinary = "Subnautica.exe"
    GameDataPath = ""
    GameDocumentsDirectory = r"%GAME_PATH%"
    GameSavesDirectory = r"%GAME_PATH%\SNAppData\SavedGames"

    _forced_libraries = ["winhttp.dll"]

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = BasicModDataChecker(
            subnautica_file_patterns
        )
        return True

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        return [
            mobase.ExecutableForcedLoadSetting(self.binaryName(), lib).withEnabled(True)
            for lib in self._forced_libraries
        ]
