from PyQt6.QtCore import QFileInfo

import mobase

from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_game import BasicGame


class SaintsRow3Game(BasicGame):
    Name = "Saints Row: The Third Support Plugin"
    Author = "peezee"
    Version = "1.0.0"

    GameName = "Saints Row: The Third"
    GameShortName = "saintsrow3"
    GameBinary = "SaintsRowTheThird.exe"
    GameDataPath = ""
    GameSteamId = 55230
    GameGogId = 1430740694
    #GameIniFiles = "display.ini" # Doesn't work for some reason
    #GameNexusId = # No idea how to get it, most mods aren't on Nexus anyway
    #GameSavesDirectory = #Need to get it from user-prefixed steam cloud directory
    
    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(
            BasicModDataChecker(
                GlobPatterns(
                    valid=[
                        "*.xtbl",
                        "*.str2_pc",
                        "*.asm_pc",
                        "*.cvbm_pc",
                        "*.cmorph_pc",
                        "*.bnk_pc",
                        "*.gpeg_pc",
                        "*.cpeg_pc",
                        "*.le_strings",
                        "*.asi",
                        "packfiles",
                        "videos",
                        "*.txt"
                    ],
                    move={
                        "*.vpp_pc": "packfiles/pc/cache/",
                        "*.bik": "videos/"
                    }
                )
            ),
        )
        return True

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Saints Row: The Third (DX11)", QFileInfo(self.gameDirectory(), "SaintsRowTheThird_DX11.exe")
            ),
            mobase.ExecutableInfo(
                "Saints Row: The Third (DX9)", QFileInfo(self.gameDirectory(), "SaintsRowTheThird.exe")
            ),
            mobase.ExecutableInfo(
                "Saints Row: The Third (Launcher)", QFileInfo(self.gameDirectory(), "game_launcher.exe")
            )
        ]