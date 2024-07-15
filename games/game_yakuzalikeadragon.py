from __future__ import annotations

import os

import mobase
from PyQt5.QtCore import QFileInfo

from ..basic_game import BasicGame
from .yakuza.yakuza_series import YakuzaGameModDataChecker, yakuza_check_rmm, yakuza_import_mods


class Yakuza6Game(BasicGame):

    __yakuza_exe_dir = os.path.join('runtime', 'media')

    Name = "Yakuza: Like a Dragon Support Plugin"
    Author = "SutandoTsukai181"
    Version = "1.0.0"

    GameName = "Yakuza: Like a Dragon"
    GameShortName = "yakuzalikeadragon"
    GameSteamId = [1235140]
    GameBinary = os.path.join(__yakuza_exe_dir, "YakuzaLikeADragon.exe")
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
        'artisan',
        'asset',
        'asset.par',
        'auth',
        'auth_e',
        'battle',
        'boot',
        'camera',
        'chara',
        'chara.par',
        'cubemap_yazawa',
        'cubemap_yazawa.par',
        'db.yazawa.de',
        'db.yazawa.de.par',
        'db.yazawa.en',
        'db.yazawa.en.par',
        'db.yazawa.es',
        'db.yazawa.es.par',
        'db.yazawa.fr',
        'db.yazawa.fr.par',
        'db.yazawa.it',
        'db.yazawa.it.par',
        'db.yazawa.ja',
        'db.yazawa.ja.par',
        'db.yazawa.ko',
        'db.yazawa.ko.par',
        'db.yazawa.pt',
        'db.yazawa.pt.par',
        'db.yazawa.ru',
        'db.yazawa.ru.par',
        'db.yazawa.zh',
        'db.yazawa.zh.par',
        'db.yazawa.zhs',
        'db.yazawa.zhs.par',
        'effect',
        'effect.par',
        'entity_table',
        'entity_yazawa',
        'entity_yazawa.par',
        'flood',
        'font.yazawa',
        'font.yazawa.par',
        'grass',
        'hact_yazawa',
        'light_anim_yazawa',
        'light_anim_yazawa.par',
        'lua',
        'lua.par',
        'map',
        'map.par',
        'minigame',
        'motion',
        'motion.par',
        'mvsfd',
        'navimesh',
        'particle',
        'particle.par',
        'patch',
        'ps5',
        'puid.yazawa',
        'reflection',
        'shader',
        'sound',
        'sound.par',
        'sound_en',
        'sound_en.par',
        'stage',
        'stream',
        'stream_en',
        'system',
        'talk_yazawa',
        'talk_yazawa.par',
        'ui.yazawa.de',
        'ui.yazawa.de.par',
        'ui.yazawa.en',
        'ui.yazawa.en.par',
        'ui.yazawa.es',
        'ui.yazawa.es.par',
        'ui.yazawa.fr',
        'ui.yazawa.fr.par',
        'ui.yazawa.it',
        'ui.yazawa.it.par',
        'ui.yazawa.ja',
        'ui.yazawa.ja.par',
        'ui.yazawa.ko',
        'ui.yazawa.ko.par',
        'ui.yazawa.pt',
        'ui.yazawa.pt.par',
        'ui.yazawa.ru',
        'ui.yazawa.ru.par',
        'ui.yazawa.zh',
        'ui.yazawa.zh.par',
        'ui.yazawa.zhs',
        'ui.yazawa.zhs.par',
        'version',
    }
