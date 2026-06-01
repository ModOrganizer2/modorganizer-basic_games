from collections.abc import Mapping
from pathlib import Path

from PyQt6.QtCore import QDateTime

import mobase

from ...basic_features.basic_save_game_info import (
    BasicGameSaveGame,
    format_date,
)


class FF12SaveGame(BasicGameSaveGame):
    def __init__(self, filepath: Path):
        super().__init__(filepath)
        f_stat = self._filepath.stat()
        self._size = f_stat.st_size
        self._created = f_stat.st_birthtime
        self._modified = f_stat.st_mtime

    def getName(self) -> str:
        return f"Slot {self.getSlot()}"

    def getSaveGroupIdentifier(self) -> str:
        return "Default"

    def getSlot(self) -> str:
        return int(self._filepath.stem[6:9])

    def getSize(self) -> int:
        return self._size

    def getBirthTime(self) -> QDateTime:
        return QDateTime.fromSecsSinceEpoch(int(self._created))

    def getCreationTime(self) -> QDateTime:
        return QDateTime.fromSecsSinceEpoch(int(self._modified))


def getSaveMetadata(savepath: Path, save: mobase.ISaveGame) -> Mapping[str, str]:
    assert isinstance(save, FF12SaveGame)
    return {
        "Slot": save.getSlot(),
        "Size": f"{save.getSize() / 1024:.2f} KB",
        "Created At": format_date(save.getBirthTime()),
        "Last Saved": format_date(save.getCreationTime()),
    }
