from enum import StrEnum

import mobase


class SettingName(StrEnum):
    AUTO_STEAM_ID = "autoSteamId"
    STEAM_ID_64 = "steamId64"
    DISABLE_AUTO_UPDATES = "disableAutoUpdates"
    SKIP_UPDATE_VERSION = "skipUpdateVersion"
    SKIP_UPDATE_UNTIL_DATE = "skipUpdateUntilDate"


class SettingsManager:
    _instance: "SettingsManager | None" = None

    def __init__(self, organizer: mobase.IOrganizer, game_name: str):
        self._organizer = organizer
        self._game_name = game_name
        SettingsManager._instance = self

    @staticmethod
    def get_instance() -> "SettingsManager":
        if SettingsManager._instance is None:
            raise RuntimeError("SettingsManager not initialized.")
        return SettingsManager._instance

    def get_setting(self, key: str) -> mobase.MoVariant:
        return self._organizer.pluginSetting(self._game_name, key)

    def set_setting(self, key: str, value: mobase.MoVariant) -> None:
        self._organizer.setPluginSetting(self._game_name, key, value)


def settings_manager() -> SettingsManager:
    return SettingsManager.get_instance()
