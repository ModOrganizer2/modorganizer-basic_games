# -*- encoding: utf-8 -*-
import datetime
import os
import struct
import sys
import time
from pathlib import Path
from typing import List

from PyQt6.QtCore import QDateTime, QDir, QFile, QFileInfo, Qt
from PyQt6.QtGui import QPainter, QPixmap

import mobase

from ..basic_features.basic_save_game_info import (
    BasicGameSaveGame,
    BasicGameSaveGameInfo,
    BasicGameSaveGameInfoWidget,
)
from ..basic_game import BasicGame


class BlackAndWhite2ModDataChecker(mobase.ModDataChecker):
    _validFolderTree = {
        "<black & white 2>": ["audio", "data", "plugins", "scripts"],
        "audio": ["dialogue", "music", "sfx"],
        "music": [
            "buildingmusic",
            "chant",
            "cutscene",
            "dynamic music",
            "epicspell",
            "townalignment",
        ],
        "sfx": ["atmos", "creature", "game", "script", "spells", "video", "grass"],
        "data": [
            "art",
            "balance",
            "ctr",
            "effects",
            "encryptedshaders",
            "font",
            "handdemo",
            "interface",
            "landscape",
            "light particle effects",
            "lipsync",
            "physics",
            "sfx",
            "shaders",
            "symbols",
            "text",
            "textures",
            "tutorial avi",
            "visualeffects",
            "weathersystem",
            "zones",
        ],
        "art": [
            "binary_anim_libs",
            "binary_animations",
            "features",
            "models",
            "skins",
            "textures",
            "water",
        ],
        "ctr": [
            "badvisor_evil",
            "badvisor_good",
            "bape",
            "bgorilla",
            "bhand",
            "blion",
            "btiger",
            "bwolf",
            "damage",
            "siren",
        ],
        "font": ["asian"],
        "asian": ["korean", "traditional chinese"],
        "landscape": [
            "aztec",
            "bw2",
            "egyptian",
            "generic",
            "greek",
            "japanese",
            "norse",
            "skysettings",
        ],
        "tutorial avi": ["placeholder", "stills"],
        "visualeffects": ["textures"],
        "scripts": ["bw2"],
    }
    _validFileLocation = {
        "<black & white 2>": ["exe", "dll", "ico", "png", "jpeg", "jpg"]
    }
    _mapFile = ["chl", "bmp", "bwe", "ter", "pat", "xml", "wal", "txt"]
    _fileIgnore = ["readme", "read me", "meta.ini", "thumbs.db", "backup", ".png"]

    def fix(self, tree: mobase.IFileTree):
        toMove = []
        for entry in tree:
            if any([sub in entry.name().casefold() for sub in self._fileIgnore]):
                continue
            elif entry.suffix() == "chl":
                toMove.append((entry, "/Scripts/BW2/"))
            elif entry.suffix() == "bmp":
                toMove.append((entry, "/Data/"))
            elif entry.suffix() == "txt":
                toMove.append((entry, "/Scripts/"))
            else:
                toMove.append((entry, "/Data/landscape/BW2/"))

        for (entry, path) in toMove:
            tree.move(entry, path, policy=mobase.IFileTree.MERGE)

        return tree

    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        # qInfo("Data validation start")
        root = tree
        unpackagedMap = False

        for entry in tree:
            entryName = entry.name().casefold()
            canIgnore = any([sub in entryName for sub in self._fileIgnore])
            if not canIgnore:
                parent = entry.parent()
                if parent is not None:

                    if parent != root:
                        parentName = parent.name().casefold()
                    else:
                        # qInfo(str(entryName))
                        parentName = "<black & white 2>"

                    if not entry.isDir():
                        if parentName in self._validFileLocation.keys():
                            if (
                                entry.suffix()
                                not in self._validFileLocation[parentName]
                            ):
                                if (
                                    entry.suffix() in self._mapFile
                                    or entryName == "map.txt"
                                ):
                                    unpackagedMap = True
                                else:
                                    return mobase.ModDataChecker.INVALID
                    else:
                        unpackagedMap = False
                        if parentName in self._validFolderTree.keys():
                            if entryName not in self._validFolderTree[parentName]:
                                return mobase.ModDataChecker.INVALID

        # qInfo(str(unpackagedMap))
        if unpackagedMap:
            return mobase.ModDataChecker.FIXABLE
        else:
            return mobase.ModDataChecker.VALID


class BlackAndWhite2SaveGame(BasicGameSaveGame):
    _saveInfLayout = {
        "start": [0x00000000, 0x00000004],
        "name": [0x00000004, 0x0000002C],
        "empty": [0x0000002C, 0x00000104],
        "land": [0x00000104, 0x00000108],
        "date": [0x00000108, 0x00000110],
        "empty1": [0x00000110, 0x00000114],
        "elapsed": [0x00000114, 0x00000118],
        "empty2": [0x00000108, 0x0000011C],
    }

    def __init__(self, filepath):
        super().__init__(filepath)
        self._filepath = Path(filepath)
        self.name: str = ""
        self.land: int = -1
        self.elapsed: int = 0
        self.lastsave: int = 0
        with open(self._filepath.joinpath("SaveGame.inf"), "rb") as info:
            # Name embedded in "SaveGame.inf" with UTF-16 encoding
            self.name = self.readInf(info, "name").decode("utf-16")
            # Land number embedded in "SaveGame.inf" as an int written in binary
            self.land = int.from_bytes(self.readInf(info, "land"), "little")
            # Getting elapsed time in second
            self.elapsed = int.from_bytes(self.readInf(info, "elapsed"), "little")
            # Getting date in 100th of nanosecond need to convert NT time
            # to UNIX time and offset localtime
            self.lastsave = (
                (
                    struct.unpack("q", self.readInf(info, "date"))[0] / 10000
                    - 11644473600000
                )
            ) - (time.localtime().tm_gmtoff * 1000)
            info.close()

    def readInf(self, inf, key):
        inf.seek(self._saveInfLayout[key][0])
        return inf.read(self._saveInfLayout[key][1] - self._saveInfLayout[key][0])

    def allFiles(self) -> List[str]:
        files = [str(file) for file in self._filepath.glob("./*")]
        files.append(str(self._filepath))
        return files

    def getCreationTime(self) -> QDateTime:
        time = QDateTime.fromMSecsSinceEpoch(self.lastsave)
        return time

    def getElapsed(self) -> str:
        return str(datetime.timedelta(seconds=self.elapsed))

    def getName(self) -> str:
        return self.name

    def getLand(self) -> str:
        return str(self.land)

    def getSaveGroupIdentifier(self):
        return self._filepath.parent.parent.name


class BlackAndWhite2LocalSavegames(mobase.LocalSavegames):
    def __init__(self, myGameSaveDir):
        super().__init__()
        self._savesDir = myGameSaveDir.absolutePath()

    def mappings(self, profile_save_dir):
        m = mobase.Mapping()

        m.createTarget = True
        m.isDirectory = True
        m.source = profile_save_dir.absolutePath()
        m.destination = self._savesDir

        return [m]

    def prepareProfile(self, profile):
        return profile.localSavesEnabled()


def getPreview(save):
    save = BlackAndWhite2SaveGame(save)
    lines = [
        [
            ("Name : " + save.getName(), Qt.AlignLeft),
            ("| Profile : " + save.getSaveGroupIdentifier()[1:], Qt.AlignLeft),
        ],
        [("Land number : " + save.getLand(), Qt.AlignLeft)],
        [("Saved at : " + save.getCreationTime().toString(), Qt.AlignLeft)],
        [("Elapsed time : " + save.getElapsed(), Qt.AlignLeft)],
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
            if align != Qt.AlignLeft:
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


class BlackAndWhite2SaveGameInfoWidget(BasicGameSaveGameInfoWidget):
    def setSave(self, save: mobase.ISaveGame):
        # Resize the label to (0, 0) to hide it:
        self.resize(0, 0)

        # Retrieve the pixmap:
        value = self._get_preview(Path(save.getFilepath()))

        if value is None:
            return

        elif isinstance(value, QPixmap):
            pixmap = value
        else:
            print(
                "Failed to retrieve the preview, bad return type: {}.".format(
                    type(value)
                ),
                file=sys.stderr,
            )
            return

        # Scale the pixmap and show it:
        # pixmap = pixmap.scaledToWidth(pixmap.width())
        self._label.setPixmap(pixmap)
        self.resize(pixmap.width(), pixmap.height())


class BlackAndWhite2SaveGameInfo(BasicGameSaveGameInfo):
    def getSaveGameWidget(self, parent=None):
        if self._get_preview is not None:
            return BasicGameSaveGameInfoWidget(parent, self._get_preview)
        return None


PSTART_MENU = (
    str(os.getenv("ProgramData")) + "\\Microsoft\\Windows\\Start Menu\\Programs"
)


class BlackAndWhite2Game(BasicGame, mobase.IPluginFileMapper):

    Name = "Black & White 2 Support Plugin"
    Author = "Ilyu"
    Version = "1.0.1"

    GameName = "Black & White 2"
    GameShortName = "BW2"
    GameNexusName = "blackandwhite2"
    GameDataPath = "%GAME_PATH%"
    GameBinary = "white.exe"
    GameDocumentsDirectory = "%DOCUMENTS%/Black & White 2"
    GameSavesDirectory = "%GAME_DOCUMENTS%/Profiles"
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Black-&-White-2"
    )

    _program_link = PSTART_MENU + "\\Black & White 2\\Black & White® 2.lnk"

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)

    def init(self, organizer: mobase.IOrganizer) -> bool:
        BasicGame.init(self, organizer)
        self._featureMap[mobase.ModDataChecker] = BlackAndWhite2ModDataChecker()
        self._featureMap[mobase.LocalSavegames] = BlackAndWhite2LocalSavegames(
            self.savesDirectory()
        )
        self._featureMap[mobase.SaveGameInfo] = BlackAndWhite2SaveGameInfo(getPreview)
        return True

    def detectGame(self):
        super().detectGame()

        program_path = Path(self._program_link)
        if program_path.exists():
            installation_path = Path(QFileInfo(self._program_link).symLinkTarget())
            if installation_path.exists():
                self.setGamePath(installation_path.parent)

        return

    def executables(self) -> List[mobase.ExecutableInfo]:
        execs = super().executables()

        """
        A bat file to load modded executables from VFS.
        """
        workaroundPath = self._gamePath + "/" + self.GameBinary[:-4] + ".bat"

        try:
            workaround = open(workaroundPath, "rt")
        except FileNotFoundError:
            with open(workaroundPath, "wt") as workaround:
                workaround.write('start "" "' + self.GameBinary + '"')
        workaround.close()

        execs.append(
            mobase.ExecutableInfo(
                self.GameShortName + " Modded Exec", QFileInfo(workaroundPath)
            )
        )

        return execs

    def listSaves(self, folder: QDir) -> List[mobase.ISaveGame]:
        profiles = list()
        for path in Path(folder.absolutePath()).glob("*/Saved Games/*"):
            if (
                path.name == "Autosave"
                or path.name == "Pictures"
                or "_invalid" in path.name
            ):
                continue
            if path.is_dir():
                saveFolder = QDir(str(path))
                if not saveFolder.exists("SaveGame.inf"):
                    savePath = saveFolder.absolutePath()
                    QFile.rename(savePath, savePath + "_invalid")
                    continue
            else:
                continue

            profiles.append(path)

        return [BlackAndWhite2SaveGame(path) for path in profiles]


class BOTGGame(BlackAndWhite2Game):

    Name = "Black & White 2 Battle of the Gods Support Plugin"

    GameName = "Black & White 2 Battle of the Gods"
    GameShortName = "BOTG"
    GameBinary = "BattleOfTheGods.exe"
    GameDocumentsDirectory = "%DOCUMENTS%/Black & White 2 - Battle of the Gods"
    GameSavesDirectory = "%GAME_DOCUMENTS%/Profiles"

    _program_link = (
        PSTART_MENU + "\\Black & White 2 Battle of the Gods"
        "\\Black & White® 2 Battle of the Gods.lnk"
    )
