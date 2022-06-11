from __future__ import annotations

import os

import mobase
from PyQt5.QtCore import QFileInfo

from ..basic_game import BasicGame
from .yakuza.yakuza_series import YakuzaGameModDataChecker, yakuza_check_rmm, yakuza_import_mods


class Yakuza4RemasteredGame(BasicGame):

    __yakuza_exe_dir = ''

    Name = "Yakuza 4 Remastered Support Plugin"
    Author = "SutandoTsukai181"
    Version = "1.0.0"

    GameName = "Yakuza 4 Remastered"
    GameShortName = "yakuza4remastered"
    GameSteamId = [1105500]
    GameBinary = os.path.join(__yakuza_exe_dir, "Yakuza4.exe")
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
        '2d',
        'auth',
        'battle',
        'bootpar',
        'chara',
        'chara_arc',
        'chara_common',
        'chasepar',
        'db.soul',
        'effect',
        'effect.par',
        'enemy_dispose',
        'font_hd',
        'font_hd.par',
        'fontpar',
        'hact',
        'ikusei',
        'light_anim',
        'map_en',
        'map_ja',
        'map_ko',
        'map_zh',
        'minigame',
        'motion',
        'mvuen',
        'mvusm',
        'pausepar',
        'pre_btl_cam',
        'puid.soul',
        'reactive_obj',
        'savedata',
        'savedata.par',
        'scenario_en',
        'scenario_ja',
        'scenario_ko',
        'scenario_zh',
        'shader',
        'snda2',
        'staffrollpar',
        'stage',
        'tougijyo',
        'tougijyo.par',
        'wdr_par_en',
        'wdr_par_ja',
        'wdr_par_ko',
        'wdr_par_zh',
    }
