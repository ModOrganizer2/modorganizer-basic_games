from __future__ import annotations

import os

import mobase
from PyQt5.QtCore import QFileInfo

from ..basic_game import BasicGame
from .yakuza.yakuza_series import YakuzaGameModDataChecker, yakuza_check_rmm, yakuza_import_mods


class Yakuza6Game(BasicGame):

    __yakuza_exe_dir = ''

    Name = "Yakuza 6 Support Plugin"
    Author = "SutandoTsukai181"
    Version = "1.0.0"

    GameName = "Yakuza 6: The Song of Life"
    GameShortName = "yakuza6"
    GameSteamId = [1388590]
    GameBinary = os.path.join(__yakuza_exe_dir, "Yakuza6.exe")
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
        '3dlut',
        'asset',
        'asset.par',
        'auth',
        'boot',
        'camera',
        'chara',
        'chara.par',
        'cubemap',
        'cubemap.par',
        'db',
        'drama_scanner',
        'drama_scanner.par',
        'effect',
        'effect.par',
        'entity',
        'entity.par',
        'entity_table',
        'flood',
        'font',
        'font.par',
        'hact',
        'light_anim',
        'lua',
        'lua.par',
        'map',
        'map.par',
        'minigame',
        'motion',
        'motion.par',
        'movie',
        'particle',
        'particle.par',
        'puid',
        'shader',
        'sound',
        'sound.par',
        'stage',
        'stream',
        'talk',
        'talk.par',
        'ui',
        'ui.par',
    }
