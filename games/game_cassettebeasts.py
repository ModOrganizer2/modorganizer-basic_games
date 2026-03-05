from collections.abc import Mapping
from io import BytesIO
import json
import mobase
import math
import os
import shutil
import struct
import sys
import zlib

from pathlib import Path
from functools import cached_property

from ..basic_features import BasicLocalSavegames
from ..basic_features.basic_save_game_info import (BasicGameSaveGame,BasicGameSaveGameInfo)
from ..basic_game import BasicGame

from PyQt6.QtCore import QDateTime, QDir, QFile, QFileInfo


class CassetteBeastsModDataChecker(mobase.ModDataChecker):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self.organizer: mobase.IOrganizer = organizer

    def dataLooksValid(self, filetree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        for e in filetree:
            if e is not None and e.isFile() and e.suffix().casefold() == "pck":
                return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.FIXABLE

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        GameDataPath = self.organizer.managedGame().GameDataPath + "/"
        treefixed = 0
        for branch in filetree:
            mod_name = filetree.name()
            if mod_name == "":
                mod_name = branch.name()
            mod_path = os.path.join(self.organizer.modsPath(), mod_name)
            if filetree.createOrphanTree("OrphanTree") is None and os.path.exists(mod_path) and branch.suffix().casefold() == "pck":
                os.makedirs(os.path.join(mod_path, GameDataPath), exist_ok=True)
                shutil.move(os.path.join(mod_path, branch.name()), os.path.join(mod_path, GameDataPath, branch.name()))
                treefixed = 1
            else:
                if branch is not None:
                    if branch.isDir():
                        for e in branch:
                            if e is not None and e.isFile() and e.suffix().casefold() == "pck":
                                filetree.move(e, GameDataPath, mobase.IFileTree.MERGE)
                                treefixed = 1
                    elif branch.suffix().casefold() == "pck":
                        filetree.move(branch, GameDataPath, mobase.IFileTree.MERGE)
                        treefixed = 1
        if treefixed == 0:
            return None
        return filetree

class CassetteBlock:
    def __init__(self):
        compressed_size = None
        data = None

class CassetteBeastsSaveGame(BasicGameSaveGame):
    def __init__(self, filepath: Path):
        super().__init__(filepath)
        self.name: str = ""
        self.cheated: str = ""
        self.lastsave: int = 0
        self.elapsed: int = 0
        info = bytearray()
        data = bytes()

        with open(filepath, 'rb') as infile:
            magic_string = infile.read(4)

            compression_mode, blocksize, raw_size = struct.unpack("III", infile.read(12))

            num_blocks = math.ceil(raw_size / blocksize)

            blocks = []

            for bnum in range(num_blocks):
              block = CassetteBlock()
              block.compressed_size = struct.unpack("I", infile.read(4))[0]
              blocks.append(block)

            for block in blocks:
              block.data = infile.read(block.compressed_size)

            magic_string = infile.read(4)
            infile.close()
        
        for block in blocks:
            data = zlib.decompress(block.data, wbits=40, bufsize=blocksize)
            info = info + data
                
        save_data = json.load(BytesIO(info))
        self.name = save_data["party"]["player"]["custom"]["name"]
        self.cheated = save_data["has_cheated"]

    def getName(self) -> str:
        return self.name

    def getCheated(self) -> str:
        return self.cheated

def getMetadata(p: Path, save: mobase.ISaveGame) -> Mapping[str, str]:
    return {
        "Character": save.getName(),
        "Cheated": save.getCheated()
    }

class CassetteBeastsGame(BasicGame):
    appdataenv = os.getenv("APPDATA")

    Name = "Cassette Beasts Support Plugin"
    Author = "modworkshop"
    Version = "1"
    GameName = "Cassette Beasts"
    GameShortName = "cassette-beasts"
    GameSteamId = 1321440
    GameBinary = "CassetteBeasts.exe"
    GameDataPath = appdataenv + "/CassetteBeasts/mods"
    GameDocumentsDirectory = appdataenv + "/CassetteBeasts"
    GameSaveExtension = "gcpf"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = CassetteBeastsModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        self._register_feature(BasicLocalSavegames(self))
        self._register_feature(
            BasicGameSaveGameInfo(None, getMetadata)
        )
        return True

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Cassette Beasts (Mods)",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ).withArgument("-load-mods"),
            mobase.ExecutableInfo(
                "Cassette Beasts (No Mods)",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
        ]

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        ext = self._mappings.savegameExtension.get()
        return [
            CassetteBeastsSaveGame(path)
            for path in Path(folder.absolutePath()).glob(f"*.{ext}")
        ]

    @cached_property
    def _base_dlls(self) -> set[str]:
        base_dir = Path(self.gameDirectory().absolutePath())
        return {str(f.relative_to(base_dir)) for f in base_dir.glob("*.dll")}

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        try:
            efls = super().executableForcedLoads()
        except AttributeError:
            efls = []
        libs: set[str] = set()
        tree: mobase.IFileTree | mobase.FileTreeEntry | None = self._organizer.virtualFileTree()
        if type(tree) is not mobase.IFileTree:
            return efls
        for e in tree:
            relpath = e.pathFrom(tree)
            if relpath and e.hasSuffix("dll") and relpath not in self._base_dlls:
                libs.add(relpath)
        exes = self.executables()
        efls = efls + [mobase.ExecutableForcedLoadSetting(exe.binary().fileName(), lib).withEnabled(True) for lib in libs for exe in exes]
        return efls

    def iniFiles(self):
        return ["settings.cfg", "mod_settings.cfg"]

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        modsPath = self.dataDirectory().absolutePath()
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)
        super().initializeProfile(directory, settings)
