# -*- encoding: utf-8 -*-
import os
from pathlib import Path
from typing import List

from PyQt5.QtCore import QDir, QFileInfo

import mobase

from ..basic_game import BasicGame, BasicGameSaveGame


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
    _validFileLocation = {"<black & white 2>": ["exe", "dll", "ico", "ini"]}

    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:

        for entry in tree:
            entryName = entry.name().casefold()
            if "readme" not in entryName:
                parent = entry.parent()
                if parent is not None:

                    if parent.parent() is not None:
                        parentName = parent.name().casefold()
                    else:
                        parentName = "<black & white 2>"

                    if not entry.isDir():
                        if parentName in self._validFileLocation.keys():
                            if (
                                entry.suffix()
                                not in self._validFileLocation[parentName]
                            ):
                                return mobase.ModDataChecker.INVALID
                    else:
                        if parentName not in self._validFolderTree.keys():
                            return mobase.ModDataChecker.INVALID
                        if entryName not in self._validFolderTree[parentName]:
                            return mobase.ModDataChecker.INVALID

        return mobase.ModDataChecker.VALID


class BlackAndWhite2SaveGame(BasicGameSaveGame):
    def __init__(self, filepath):
        super().__init__(filepath)
        self.name: str = ""

    def allFiles(self) -> List[str]:
        return [str(file) for file in self._filepath.glob("*") if file.is_file()]

    def getName(self) -> str:
        with open(self._filepath.joinpath("SaveGame.inf"), "rb") as info:
            info.read(4)
            name = u""
            while True:
                char = info.read(2)
                name = name + char.decode("utf-16")
                if char[0] == 0:
                    break
            info.close()
            return name
        return super.getName()

    def getSaveGroupIdentifier(self):
        return self._filepath.parent.parent.name


pstart_menu = (
    str(os.getenv("ProgramData")) + "\\Microsoft\\Windows\\Start Menu\\Programs"
)


class BlackAndWhite2Game(BasicGame):

    Name = "Black & White 2 Support Plugin"
    Author = "Ilyu"
    Version = "0.5.0"

    GameName = "Black & White 2"
    GameShortName = "BW2"
    GameNexusName = "blackandwhite2"
    GameDataPath = "%GAME_PATH%"
    GameBinary = "white.exe"
    GameDocumentsDirectory = "%DOCUMENTS%/Black & White 2"
    GameSavesDirectory = "%GAME_DOCUMENTS%/Profiles"

    _program_link = pstart_menu + "\\Black & White 2\\Black & White® 2.lnk"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = BlackAndWhite2ModDataChecker()
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
            if path.name == "Autosave" or path.name == "Pictures":
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
        pstart_menu
        + "Black & White 2 Battle of the Gods\\Black & White® 2 Battle of the Gods.lnk"
    )
