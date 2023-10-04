import mobase
from PyQt6.QtCore import QDir


class BasicLocalSavegames(mobase.LocalSavegames):
    def __init__(self, game_save_dir: QDir):
        super().__init__()
        self._game_saves_dir = game_save_dir.absolutePath()

    def mappings(self, profile_save_dir: QDir):
        return [
            mobase.Mapping(
                source=profile_save_dir.absolutePath(),
                destination=self._game_saves_dir,
                is_directory=True,
                create_target=True,
            )
        ]

    def prepareProfile(self, profile: mobase.IProfile) -> bool:
        return profile.localSavesEnabled()
