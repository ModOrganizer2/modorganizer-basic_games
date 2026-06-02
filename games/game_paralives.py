# from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_game import BasicGame


class ParalivesGame(BasicGame):
    # Plugin name
    Name = "Paralives"
    Author = "Julian Noel"
    Version = "0.1.1"

    # actual game name
    GameName = "Paralives"

    # Internal game ID used by MO2
    GameShortName = "paralives"

    # The nexus mods page identifier (if applicable)
    GameNexusName = "paralives"

    # The main executable MO2 will look for to verify the folder
    GameBinary = "Paralives.exe"

    # TODO
    GameDocumentsDirectory = "%USERPROFILE%/AppData/LocalLow/Paralives/Paralives/ModOrganizer"
    GameSavesDirectory = (
        "%USERPROFILE%/AppData/LocalLow/Paralives/Paralives/MySavedGames.mod"
    )

    # framework includes special variables like %GAME_DOCUMENTS% to override the
    # default relative path semantics; absolute paths will be treated as absolutes
    # relatives will be done relative to the actual game directory
    GameDataPath = "%GAME_DOCUMENTS%"

    # Steam App ID for auto-detection
    GameSteamId = 1119730
    # maybe - it's actually really hard to find this
    GameNexusId = 9002

    # TODO: save handling (it is in the localappdata folder but should be excluded)

    def __init__(self):
        super().__init__()
        # self._featureMap[mobase.ModDataChecker] = BasicModDataChecker(
        #     #describe what operation, and what matches to perform them on
        #     GlobPatterns(
        #         #valid files findable in a mod
        #         valid=[
        #             "meta.ini",  # Included in installed mod folder.
        #             "BepInEx",
        #             "doorstop_libs",
        #             "unstripped_corlib",
        #             "doorstop_config.ini",
        #             "start_game_bepinex.sh",
        #             "start_server_bepinex.sh",
        #             "winhttp.dll",
        #             #
        #             "InSlimVML",
        #             "Paralives_Data",
        #             "inslimvml.ini",
        #             #
        #             "unstripped_managed",
        #             #
        #             "AdvancedBuilder",
        #         ],
        #         # mod authors will add these but they
        #         # are not needed for deployment and will often
        #         # conflict with each other anyway.
        #         delete=[
        #             #readmes, helpers, etc
        #             "*.txt",
        #             "*.md",
        #             "README",
        #             "icon.png",
        #             "license",
        #             #package crap
        #             "manifest.json",
        #             #debug crap
        #             "*.dll.mdb",
        #             "*.pdb",
        #         ],
        #         #TODO: check basic_games to see if expanded variables work here
        #         #we need to move these files into the
        #         # bepinex dirs instead of the default location
        #         move={
        #             # part of BepInEx script mod support
        #             "plugins": "BepInEx/",
        #             "*.dll": "BepInEx/plugins/",
        #             "*.xml": "BepInEx/plugins/",
        #             "config": "BepInEx/",
        #             "*.cfg": "BepInEx/config/",
        #         }
        #     )
        # )

    # TODO: savegame handling (since it lives in the same folder as the content mods but is NOT a content mod)
