# -*- encoding: utf-8 -*-

import os

from typing import Callable

from PyQt5.QtCore import QDateTime, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout

import mobase


class BasicGameSaveGame(mobase.ISaveGame):
    def __init__(self, filename):
        super().__init__()
        self._filename = filename

    def getFilename(self):
        return self._filename

    def getCreationTime(self):
        return QDateTime(os.path.getmtime(self._filename))

    def getSaveGroupIdentifier(self):
        return ""

    def allFiles(self):
        return [self._filename]

    def hasScriptExtenderFile(self):
        return False


class BasicGameSaveGameInfoWidget(mobase.ISaveGameInfoWidget):
    #     self._label = QLabel(parent)

    # def setSave(self, filename):
    #     print("setSave")
    #     pixmap = QPixmap(
    #         r"D:\Documents\The Witcher 3\gamesaves\AutoSave_54bde_7e22c000_5af7dca.png"
    #     )
    #     print(pixmap)
    #     self._label.setPixmap(pixmap)
    #     self.resize(250, 250)
    #     return self._label

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

    def setSave(self, filename):
        pixmap = QPixmap(self._get_preview(filename))
        pixmap = pixmap.scaledToWidth(320)
        self.setWindowTitle("The Title: {}".format(filename))
        self._label.setPixmap(pixmap)
        self.resize(pixmap.width(), pixmap.height())


class BasicGameSaveGameInfo(mobase.SaveGameInfo):
    def __init__(self, get_preview: Callable[[str], str]):
        super().__init__()
        self._get_preview = get_preview

    def getSaveGameInfo(self, filename):
        return BasicGameSaveGame(filename)

    def getMissingAssets(self, filename):
        return {}

    def getSaveGameWidget(self, parent=None):
        return BasicGameSaveGameInfoWidget(parent, self._get_preview)

    def hasScriptExtenderSave(self, filename):
        return False
