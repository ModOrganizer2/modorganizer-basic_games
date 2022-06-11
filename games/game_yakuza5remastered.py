from __future__ import annotations

import os

import mobase
from PyQt5.QtCore import QFileInfo

from ..basic_game import BasicGame
from .yakuza.yakuza_series import YakuzaGameModDataChecker, yakuza_check_rmm, yakuza_import_mods


class Yakuza5RemasteredGame(BasicGame):

    __yakuza_exe_dir = 'main'

    Name = "Yakuza 5 Remastered Support Plugin"
    Author = "SutandoTsukai181"
    Version = "1.0.0"

    GameName = "Yakuza 5 Remastered"
    GameShortName = "yakuza5remastered"
    GameSteamId = [1105510]
    GameBinary = os.path.join(__yakuza_exe_dir, "Yakuza5.exe")
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
        'auth',
        'auth_telop',
        'battlepar',
        'bootpar',
        'chara',
        'chara.par',
        'chara_arc',
        'chara_common',
        'db.devil',
        'effect',
        'effect.par',
        'fighter',
        'fontpar',
        'hact',
        'light_anim',
        'm2ftg',
        'map_par_hd',
        'minigame_en',
        'minigame_ja',
        'minigame_ko',
        'minigame_zh',
        'module',
        'motion',
        'mvstm',
        'pausepar',
        'puid.devil',
        'reactorpar',
        'scenario',
        'scenario_en',
        'scenario_ja',
        'scenario_ko',
        'scenario_zh',
        'shader',
        'soundpar',
        'stage',
        'staypar',
        'strmen',
        'wdr_par_en',
        'wdr_par_ja',
        'wdr_par_ko',
        'wdr_par_zh',
    }
