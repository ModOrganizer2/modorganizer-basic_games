from abc import ABC
from pathlib import Path

import mobase
from PyQt6.QtCore import QDir, QDirIterator, QFileInfo
from PyQt6.QtGui import QImage

from ..basic_features import BasicGameSaveGameInfo, BasicModDataChecker, GlobPatterns
from ..basic_features.basic_save_game_info import BasicGameSaveGame
from ..basic_game import BasicGame


class BG3SaveGame(BasicGameSaveGame):
    def __init__(self, filepath: Path):
        super().__init__(filepath)
        self._filepath = filepath

    def getName(self) -> str:
        name = ""
        save_parts = self._filepath.parent.name.split("-")
        if len(save_parts) > 1:
            name = save_parts[0]
        final_name = "{}{}".format(
            f"{name} - " if name else "",
            self._filepath.stem.replace("_", " ")
        )
        return final_name


def bg3_fetch_save_image(p: Path) -> QImage:
    base_path = p.parent.absolute()
    image_file: Path = base_path / (QFileInfo(str(p)).baseName() + ".WebP")
    return QImage(str(image_file))


class BG3GamePlugin(mobase.GamePlugins, ABC):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self._organizer = organizer


class BG3Game(BasicGame):
    Name = "Baldur's Gate 3 Support Plugin"
    Author = "MO2 Team"

    GameName = "Baldur's Gate 3"
    GameShortName = "baldursgate3"
    GameBinary = r"bin\bg3.exe"
    GameDataPath = r"%LOCALAPPDATA%\\Larian Studios\\Baldur's Gate 3\\Mods"
    GameSavesDirectory = r"%LOCALAPPDATA%\\Larian Studios\\Baldur's Gate 3\\PlayerProfiles\\Public\\Savegames\\Story\\"
    GameSaveExtension = "lsv"
    GameSteamId = 1086940
    GameGogId = 1456460669
    # GameSupportURL = (
    #     r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
    #     "Game:-Dragon-Age-II"
    # )

    def version(self):
        return mobase.VersionInfo(0, 0, 1, mobase.ReleaseType.PRE_ALPHA)

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(BasicModDataChecker(
            GlobPatterns(
                valid=["*.pak"],
                delete=["info.json"],
                move={"*.pak": "/"}
            )
        ))
        self._register_feature(
            BasicGameSaveGameInfo(get_preview=bg3_fetch_save_image)
        )
        return True

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        ext = self._mappings.savegameExtension.get()
        it = QDirIterator(folder.absolutePath(), QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot,
                          QDirIterator.IteratorFlag.Subdirectories)
        saves: list[BG3SaveGame] = []
        while it.hasNext():
            save_directory = QDir(it.next())
            save_directory.setNameFilters([f"*.{ext}"])
            save_file = Path(save_directory.absolutePath()) / save_directory.entryList()[0]
            saves.append(BG3SaveGame(save_file))
        return saves
