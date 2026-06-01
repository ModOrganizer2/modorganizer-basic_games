import os
import shutil
from pathlib import Path

from PyQt6.QtCore import (
    QDateTime,
    QDir,
    QFileInfo,
    QStandardPaths,
    qInfo,
)
from PyQt6.QtWidgets import QMainWindow, QTabWidget

import mobase

from ..basic_features import BasicLocalSavegames
from ..basic_features.basic_save_game_info import BasicGameSaveGameInfo
from ..basic_game import BasicGame
from .ff12.Archive.Widget import ArchiveContainerWidget
from .ff12.AutoUpdate import UpdateChecker
from .ff12.ModDataChecker import FF12ModDataChecker
from .ff12.SaveGame import FF12SaveGame, getSaveMetadata
from .ff12.SettingsManager import SettingName, SettingsManager, settings_manager
from .ff12.SteamHelper import get_last_logged_steam_id

VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0
VERSION_RELEASE_TYPE = mobase.ReleaseType.FINAL


class FF12TZAGame(BasicGame):
    Name = "Final Fantasy XII TZA Support Plugin"
    Author = "ffgriever & Xeavin"
    GameName = "Final Fantasy XII The Zodiac Age"
    GameShortName = "finalfantasy12"
    GameNexusName = "finalfantasy12"
    GameBinary = "x64/FFXII_TZA.exe"
    GameDataPath = "%GAME_PATH%"
    GameSteamId = 595520
    GameSavesDirectory = "%GAME_DOCUMENTS%"

    _archives_tab: ArchiveContainerWidget

    def __init__(self):
        super().__init__()
        self._suppress_setting_callback = False

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        SettingsManager(organizer, self.name())
        self._register_feature(FF12ModDataChecker())
        self._register_feature(BasicLocalSavegames(self))
        self._register_feature(BasicGameSaveGameInfo(get_metadata=getSaveMetadata))
        organizer.onPluginSettingChanged(self._on_plugin_setting_changed_callback)
        organizer.onUserInterfaceInitialized(
            self._on_user_interface_initialized_callback
        )

        auto_steam_id = settings_manager().get_setting(SettingName.AUTO_STEAM_ID)
        if auto_steam_id is True:
            self._set_last_logged_steam_id()

        return True

    def version(self):
        return mobase.VersionInfo(
            VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH, VERSION_RELEASE_TYPE
        )

    def settings(self) -> list[mobase.PluginSetting]:
        return [
            mobase.PluginSetting(
                SettingName.AUTO_STEAM_ID,
                (
                    f"If true, automatically set '{SettingName.STEAM_ID_64}' to last logged Steam user."
                ),
                default_value=True,
            ),
            mobase.PluginSetting(
                SettingName.STEAM_ID_64,
                (
                    "Unique 64-bit Steam user identifier used to locate saves and configuration files. "
                    "Leave empty when launching the game without Steam."
                ),
                default_value="",
            ),
            mobase.PluginSetting(
                SettingName.DISABLE_AUTO_UPDATES,
                ("If true, disables automatic updates for the plugin."),
                default_value=False,
            ),
            mobase.PluginSetting(
                SettingName.SKIP_UPDATE_VERSION,
                ("If set, skips update dialog for this version."),
                default_value="v0.0.0",
            ),
            mobase.PluginSetting(
                SettingName.SKIP_UPDATE_UNTIL_DATE,
                (
                    "If set, skips update dialog until this date (in seconds since epoch)."
                ),
                default_value=0,
            ),
        ]

    def documentsDirectory(self) -> QDir:
        docs_path = QDir(
            QDir(
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.DocumentsLocation
                )
            ).filePath("My Games/FINAL FANTASY XII THE ZODIAC AGE")
        )

        steam_id = settings_manager().get_setting(SettingName.STEAM_ID_64)
        if isinstance(steam_id, str) and steam_id:
            docs_path = QDir(docs_path.absoluteFilePath(steam_id))

        return docs_path

    def absolutePath(self) -> str:
        return self.savesDirectory().absolutePath()

    def executables(self):
        # Windows isn't necessarily installed in "C:\Windows\".
        cmd_path = shutil.which("cmd.exe")

        # We're using cmd.exe to launch a launcher, because otherwise it can't be accessed
        # using VFS. Otherwise we would have to scan mods and detect where it actually is.
        default_launcher_path = self.gameDirectory().absoluteFilePath(
            "x64/ff12-launcher.exe"
        )

        # If launcher exists, run it, else set color to red and show message.
        launcher_cmd = (
            f'if exist "{default_launcher_path}" '
            f'("{default_launcher_path}") '
            f'else (color 0C && echo Launcher not found: "{default_launcher_path}". && echo Please install External File Loader with MO2 support. && pause && color)'
        )

        return [
            mobase.ExecutableInfo(f"{self.gameName()} (Modded)", QFileInfo(cmd_path))
            .withArgument(f"/c {launcher_cmd}")
            .withWorkingDirectory(self.gameDirectory().absoluteFilePath("x64")),
            mobase.ExecutableInfo(
                f"{self.gameName()} (Vanilla)",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
            mobase.ExecutableInfo(
                "Configuration Tool",
                QFileInfo(
                    self.gameDirectory().absoluteFilePath(
                        "x64/FFXII_TZA_GameSetting.exe"
                    )
                ),
            ),
            mobase.ExecutableInfo("Reload VFS", QFileInfo(cmd_path)).withArgument("/c"),
        ]

    def iniFiles(self):
        return ["GameSetting.ini", "keymap.ini"]

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        return [
            FF12SaveGame(path)
            for path in Path(folder.absolutePath()).glob("FFXII_???")
            if path.is_file() and path.name[6:9].isdigit()
        ]

    def _on_plugin_setting_changed_callback(
        self,
        plugin_name: str,
        setting: str,
        old: mobase.MoVariant,
        new: mobase.MoVariant,
    ):
        if plugin_name != self.name() or self._suppress_setting_callback is True:
            return

        if setting == SettingName.AUTO_STEAM_ID and old is False and new is True:
            self._suppress_setting_callback = True
            try:
                self._set_last_logged_steam_id()
            finally:
                self._suppress_setting_callback = False
        elif setting == SettingName.STEAM_ID_64 and old != new:
            if settings_manager().get_setting(SettingName.AUTO_STEAM_ID) is True:
                self._suppress_setting_callback = True
                try:
                    settings_manager().set_setting(SettingName.AUTO_STEAM_ID, False)
                finally:
                    self._suppress_setting_callback = False

    def _set_last_logged_steam_id(self):
        last_steam_id = get_last_logged_steam_id()
        if not last_steam_id:
            return

        cur_steam_id = settings_manager().get_setting(SettingName.STEAM_ID_64)
        if last_steam_id == cur_steam_id:
            return

        settings_manager().set_setting(SettingName.STEAM_ID_64, last_steam_id)
        if cur_steam_id:
            qInfo(f"Updated Steam ID from '{cur_steam_id}' to '{last_steam_id}'.")
        else:
            qInfo(f"Set Steam ID to '{last_steam_id}'.")

    def _on_user_interface_initialized_callback(self, window: QMainWindow):
        if self._organizer.managedGame() is not self:
            return

        self._add_archives_tab(window)
        self._check_for_update(window)

    def _add_archives_tab(self, window: QMainWindow):
        tab_widget: QTabWidget = window.findChild(QTabWidget, "tabWidget")
        if not tab_widget:
            return

        game_path = Path(self.gameDirectory().absolutePath())
        self._archives_tab = ArchiveContainerWidget(game_path)
        tab_widget.addTab(self._archives_tab, "Archives")

    def _check_for_update(self, window: QMainWindow):
        if settings_manager().get_setting(SettingName.DISABLE_AUTO_UPDATES) is True:
            return

        remind_time_raw = settings_manager().get_setting(
            SettingName.SKIP_UPDATE_UNTIL_DATE
        )
        remind_time = remind_time_raw if isinstance(remind_time_raw, int) else 0
        now_secs = int(QDateTime.currentDateTime().toSecsSinceEpoch())

        if remind_time > now_secs:
            return

        skip_version_raw = settings_manager().get_setting(
            SettingName.SKIP_UPDATE_VERSION
        )
        skip_version = skip_version_raw if isinstance(skip_version_raw, str) else None

        update_checker = UpdateChecker(
            "FF12 Plugin",
            "FF12-Modding",
            "FF12-MO2-Plugin",
            VERSION_MAJOR,
            VERSION_MINOR,
            VERSION_PATCH,
            VERSION_RELEASE_TYPE,
            window,
            update_targets=["game_ff12.py", "ff12"],
            remove_targets=["ff12"],
            skip_version=skip_version,
            plugin_dir=os.path.dirname(__file__),
        )

        # We're using non-modal dialogs, so we have to use callbacks to clear settings.
        def on_update_installed():
            settings_manager().set_setting(SettingName.SKIP_UPDATE_VERSION, "v0.0.0")
            settings_manager().set_setting(SettingName.SKIP_UPDATE_UNTIL_DATE, 0)

        def on_version_skipped(version: str):
            settings_manager().set_setting(SettingName.SKIP_UPDATE_VERSION, version)

        def on_update_remind(remind_time: int):
            settings_manager().set_setting(
                SettingName.SKIP_UPDATE_UNTIL_DATE, remind_time
            )

        update_checker.on_update_installed(on_update_installed)
        update_checker.on_version_skipped(on_version_skipped)
        update_checker.on_update_remind(on_update_remind)
        update_checker.check_for_update()
