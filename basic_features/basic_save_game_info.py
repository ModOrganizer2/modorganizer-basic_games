# -*- encoding: utf-8 -*-

import sys

from pathlib import Path
from typing import Callable, List, Optional, Type

from PyQt5.QtCore import QDateTime, Qt
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout

import mobase


class BasicGameSaveGame(mobase.ISaveGame):
    def __init__(self, filepath: Path):
        super().__init__()
        self._filepath = filepath

    def getFilepath(self) -> str:
        return self._filepath.as_posix()

    def getName(self) -> str:
        return self._filepath.name

    def getCreationTime(self):
        return QDateTime.fromSecsSinceEpoch(int(self._filepath.stat().st_mtime))

    def getSaveGroupIdentifier(self) -> str:
        return ""

    def allFiles(self) -> List[str]:
        return [self.getFilename()]


class BasicGameSaveGameInfoWidget(mobase.ISaveGameInfoWidget):
    def __init__(self, parent: QWidget, get_preview: Callable[[str], str]):
        super().__init__(parent)

        self._get_preview = get_preview

        layout = QVBoxLayout()
        self._label = QLabel()
        palette = self._label.palette()
        palette.setColor(self._label.foregroundRole(), Qt.white)
        self._label.setPalette(palette)
        layout.addWidget(self._label)
        self.setLayout(layout)

        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.black)
        self.setAutoFillBackground(True)
        self.setPalette(palette)

    def setSave(self, save: mobase.ISaveGame):
        # Resize the label to (0, 0) to hide it:
        self._label.resize(0, 0)

        # Retrieve the pixmap:
        value = self._get_preview(save.getFilepath())

        if value is None:
            return

        if isinstance(value, Path):
            pixmap = QPixmap(str(value))
        elif isinstance(value, str):
            pixmap = QPixmap(value)
        elif isinstance(value, QPixmap):
            pixmap = value
        elif isinstance(value, QImage):
            pixmap = QPixmap.fromImage(value)
        else:
            print(
                "Failed to retrieve the preview, bad return type: {}.".format(
                    type(value)
                ),
                file=sys.stderr,
            )
            return

        # Scale the pixmap and show it:
        pixmap = pixmap.scaledToWidth(320)
        self._label.setPixmap(pixmap)
        self.resize(pixmap.width(), pixmap.height())


class BasicGameSaveGameInfo(mobase.SaveGameInfo):
    def __init__(
        self,
        get_preview: Optional[Callable[[str], str]] = None,
        savegame_class: Type[BasicGameSaveGame] = BasicGameSaveGame,
    ):
        super().__init__()
        self._get_preview = get_preview
        self._savegame_class = savegame_class

    def getSaveGameInfo(self, filename: str):
        return self._savegame_class(filename)

    def getMissingAssets(self, filename: str):
        return {}

    def getSaveGameWidget(self, parent=None):
        if self._get_preview is not None:
            return BasicGameSaveGameInfoWidget(parent, self._get_preview)
        return None

    def hasScriptExtenderSave(self, filename: str):
        return False
