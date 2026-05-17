import mobase

from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_game import BasicGame


class PillarsOfEternityGame(BasicGame):
    Name = "Pillars of Eternity Support Plugin"
    Author = "TheForgotten69"
    Version = "1.0.0"

    GameName = "Pillars of Eternity"
    GameShortName = "pillarsofeternity"
    GameNexusName = "pillarsofeternity"
    GameNexusId = 3005
    GameSteamId = [291650]
    GameGogId = 1207658930
    GameBinary = "PillarsOfEternity.exe"
    GameDataPath = ""
    GameSaveExtension = "savegame"
    GameSavesDirectory = r"%USERPROFILE%/Saved Games/Pillars of Eternity"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(
            BasicModDataChecker(
                GlobPatterns(
                    valid=[
                        "BepInEx",
                        "PillarsOfEternity_Data",
                    ],
                    delete=[
                        "*.md",
                        "icon.png",
                        "manifest.json",
                        "fomod",
                    ],
                    move={
                        "*.dll":           "BepInEx/plugins/",
                        "assetbundles":    "PillarsOfEternity_Data/",
                        # Asset bundle folders (st_ar_*, st_en_*, st_fx_*, etc.)
                        "st_*":            "PillarsOfEternity_Data/assetbundles/",
                        "data":            "PillarsOfEternity_Data/",
                        "data_expansion1": "PillarsOfEternity_Data/",
                        "data_expansion2": "PillarsOfEternity_Data/",
                        "data_expansion3": "PillarsOfEternity_Data/",
                        "conversations":   "PillarsOfEternity_Data/data/",
                        "portraits":       "PillarsOfEternity_Data/data/art/gui/",
                        # Portrait sub-folders packaged without a portraits/ wrapper
                        "companions":      "PillarsOfEternity_Data/data/art/gui/portraits/",
                        "npcs":            "PillarsOfEternity_Data/data/art/gui/portraits/",
                        "player":          "PillarsOfEternity_Data/data/art/gui/portraits/",
                        "art":             "PillarsOfEternity_Data/data/",
                        "quests":          "PillarsOfEternity_Data/data/",
                        "spaces":          "PillarsOfEternity_Data/data/",
                        "items":           "PillarsOfEternity_Data/data/",
                        "characters":      "PillarsOfEternity_Data/data/",
                        "abilities":       "PillarsOfEternity_Data/data/",
                        "globaldata":      "PillarsOfEternity_Data/data/",
                    },
                )
            )
        )
        return True
