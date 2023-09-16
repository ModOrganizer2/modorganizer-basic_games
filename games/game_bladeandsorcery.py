from pathlib import Path
import json
import time
from time import mktime

from PyQt6.QtCore import QDateTime, Qt
from PyQt6.QtGui import QPainter, QPixmap

import mobase

from ..basic_features.basic_save_game_info import (
    BasicGameSaveGame,
    BasicGameSaveGameInfo,
    BasicGameSaveGameInfoWidget,
)

from ..basic_game import BasicGame


class BaSSaveGame(BasicGameSaveGame):
    def __init__(self, filepath):
        super().__init__(filepath)
        self._filepath = Path(filepath)
        save = open(self._filepath.joinpath("SaveGame.inf"), "rb")
        save_data = json.load(save)
        self.gameMode: str = save_data["gameModeId"]
        self.gender: str = "Male" if save_data["creatureId"] == "PlayerDefaultMale" else "Female"
        self.ethnicity: str = save_data["ethnicGroupId"]
        h, m, s = save_data["playTime"].split(":")
        self.elapsed: tuple[int, int, float] = (int(h), int(m), float(s))
        self.lastsave: time.struct_time = time.strptime(save_data["lastPlayTime"], "%Y-%m-%dT%H:%M:%S")
        self.tutorial: bool = True if save_data["Tutorial"] == "Done" else False
        self.swim: bool = save_data["tutorialFlags"]["hasLearnedToSwim"]
        self.money: float = save_data["money"]
        save.close()

    def getCreationTime(self) -> QDateTime:
        return QDateTime.fromSecsSinceEpoch(int(mktime(self.lastsave)))

    def getElapsed(self) -> str:
        return f"{self.elapsed[0]} hours, {self.elapsed[1]} minutes, {int(self.elapsed[2])} seconds"

    def getCharacter(self) -> str:
        return f"{self.gender} {self.ethnicity}"
    
    def getGameMode(self) -> str:
        return self.gameMode
    
    def getTutorial(self) -> str:
        return "Complete" if self.tutorial else "Incomplete"
    
    def getCanSwim(self) -> bool:
        return self.swim
    
    def getMoney(self) -> str:
        return str(self.money)


def getPreview(save: Path) -> QPixmap:
    save = BaSSaveGame(save)
    lines = [
        [
            ("Name : " + save.getCharacter(), Qt.AlignmentFlag.AlignLeft),
            ("- Game Mode : " + save.getGameMode(), Qt.AlignmentFlag.AlignLeft),
        ],
        [("Saved at : " + save.getCreationTime().toString(), Qt.AlignmentFlag.AlignLeft)],
        [("Elapsed time : " + save.getElapsed(), Qt.AlignmentFlag.AlignLeft)],
        [("Tutorial : " + save.getTutorial(), Qt.AlignmentFlag.AlignLeft)],
        [("Money : " + save.getMoney(), Qt.AlignmentFlag.AlignLeft)],
    ]

    pixmap = QPixmap(320, 320)
    pixmap.fill()
    # rightBuffer = []

    painter = QPainter()
    painter.begin(pixmap)
    fm = painter.fontMetrics()
    margin = 5
    height = 0
    width = 0
    ln = 0
    for line in lines:

        cHeight = 0
        cWidth = 0

        for (toPrint, align) in line:
            bRect = fm.boundingRect(toPrint)
            cHeight = bRect.height() * (ln + 1)
            bRect.moveTop(cHeight - bRect.height())
            if align != Qt.AlignmentFlag.AlignLeft:
                continue
            else:
                bRect.moveLeft(cWidth + margin)
            cWidth = cWidth + bRect.width()
            painter.drawText(bRect, align, toPrint)

        height = max(height, cHeight)
        width = max(width, cWidth + (2 * margin))
        ln = ln + 1
    # height = height + lh

    painter.end()

    return pixmap.copy(0, 0, width, height)


class BaSSaveGameInfo(BasicGameSaveGameInfo):
    def getSaveGameWidget(self, parent=None):
        if self._get_preview is not None:
            return BasicGameSaveGameInfoWidget(parent, self._get_preview)
        return None


class BaSGame(BasicGame):

    Name = "Blade & Sorcery Plugin"
    Author = "R3z Shark"
    Version = "0.1.0"

    GameName = "Blade & Sorcery"
    GameShortName = "bladeandsorcery"
    GameBinary = "BladeAndSorcery.exe"
    GameDataPath = r"BladeAndSorcery_Data\StreamingAssets\Mods"
    GameDocumentsDirectory = "%DOCUMENTS%/My Games/BladeAndSorcery"
    GameSavesDirectory = "%GAME_DOCUMENTS%/Saves/Default"
    GameSaveExtension = "chr"
    GameSteamId = 629730
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Blade-&-Sorcery"
    )

    def init(self, organizer: mobase.IOrganizer) -> bool:
        BasicGame.init(self, organizer)
        self._featureMap[mobase.SaveGameInfo] = BaSSaveGameInfo(get_preview=getPreview)
        return True
