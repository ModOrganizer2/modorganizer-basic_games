from __future__ import annotations

import os

import mobase
from PyQt5.QtCore import QFileInfo

from ..basic_game import BasicGame
from .yakuza.yakuza_series import YakuzaGameModDataChecker, yakuza_check_rmm, yakuza_import_mods


class Yakuza0Game(BasicGame):

    __yakuza_exe_dir = 'media'

    Name = "Yakuza 0 Support Plugin"
    Author = "SutandoTsukai181"
    Version = "1.0.0"

    GameName = "Yakuza 0"
    GameShortName = "yakuza0"
    GameSteamId = [638970]
    GameBinary = os.path.join(__yakuza_exe_dir, "Yakuza0.exe")
    GameDataPath = os.path.join(__yakuza_exe_dir, 'mods', '_externalMods')

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = YakuzaGameModDataChecker(self.__valid_paths)
        self._organizer.onUserInterfaceInitialized(lambda win: yakuza_check_rmm(self, win))
        self._organizer.onUserInterfaceInitialized(lambda win: yakuza_import_mods(self, win))
        return True

    def executables(self) -> list[mobase.ExecutableInfo]:
        return super().executables() + [mobase.ExecutableInfo(
            "Ryu Mod Manager",
            QFileInfo(self.gameDirectory().absoluteFilePath(
                os.path.join(self.__yakuza_exe_dir, 'RyuModManager.exe')))
        ).withArgument('--cli')]

    def settings(self) -> list[mobase.PluginSetting]:
        return super().settings() + [mobase.PluginSetting(
            'import_mods_prompt',
            'Check for mods to import from RMM mods folder on launch',
            True
        )]

    __valid_paths = {
        '2dpar',
        'auth_w64_e',
        'battlepar',
        'bootpar',
        'chara',
        'chara_arc',
        'chara_common',
        'cloth',
        'drama_scanner',
        'effect',
        'fighter',
        'flood',
        'flood.par',
        'fontpar',
        'hact',
        'hact.par',
        'light_anim',
        'loading',
        'minigame',
        'motion_w64',
        'movie_w64',
        'reactorpar',
        'scenario',
        'shader',
        'sound',
        'soundcpk',
        'soundpar',
        'stage',
        'staypar',
    }
