# -*- encoding: utf-8 -*-

import sys
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QDateTime, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

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

    def allFiles(self) -> list[str]:
        return [self.getFilepath()]


class BasicGameSaveGameInfoWidget(mobase.ISaveGameInfoWidget):
    def __init__(self, parent: QWidget, get_preview: Callable[[Path], Path | None]):
        super().__init__(parent)

        self._get_preview = get_preview

        layout = QVBoxLayout()
        self._label = QLabel()
        palette = self._label.palette()
        palette.setColor(self._label.foregroundRole(), Qt.GlobalColor.white)
        self._label.setPalette(palette)
        layout.addWidget(self._label)
        self.setLayout(layout)

        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.GlobalColor.black)
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        self.setWindowFlags(
            Qt.WindowType.ToolTip | Qt.WindowType.BypassGraphicsProxyWidget
        )

    def setSave(self, save: mobase.ISaveGame):
        # Resize the label to (0, 0) to hide it:
        self.resize(0, 0)

        # Retrieve the pixmap:
        value = self._get_preview(Path(save.getFilepath()))

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
    def __init__(self, get_preview: Callable[[Path], Path | None] | None = None):
        super().__init__()
        self._get_preview = get_preview

    def getMissingAssets(self, save: mobase.ISaveGame):
        return {}

    def getSaveGameWidget(self, parent=None):
        if self._get_preview is not None:
            return BasicGameSaveGameInfoWidget(parent, self._get_preview)
        return None
