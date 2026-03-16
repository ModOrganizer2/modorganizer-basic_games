from collections.abc import Mapping, Sequence
from datetime import datetime
from functools import cached_property
from io import BytesIO
from typing import Any, Optional
from pathlib import Path
import json
import math
import os
import shutil
import struct
import zlib

import mobase
from PyQt6.QtCore import QDateTime, QDir, QFile, QFileInfo

from ..basic_features import BasicLocalSavegames
from ..basic_features.basic_save_game_info import (BasicGameSaveGame,BasicGameSaveGameInfo)
from ..basic_game import BasicGame


def json_get_me(value: Any, path: Sequence[str | int], /, default: Any) -> Any:
    for part in path:
        if type(part) not in (str, int) or type(value) not in (dict, list):
            return default
        value = value[part]
    return value

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
        compressed_size: str = "(unknown)"
        data: str = "(unknown)"

class CassetteBeastsSaveGame(BasicGameSaveGame):
    def __init__(self, filepath: Path):
        super().__init__(filepath)
        self.name: str = "(unknown)"
        self.cheated: str = "(unknown)"
        self.lastsave: str = "(unknown)"
        self.elapsed: str = "(unknown)"
        # This doesn't state wether the game would load it,
        # only if the data was properly parsed.
        self.errorMessage: str = ""

        save_data = None
        try:
            info = bytearray()
            data = bytes()
            with open(filepath, 'rb') as infile:
                infile.read(4)

                compression_mode, blocksize, raw_size = struct.unpack("III", infile.read(12))

                num_blocks = math.ceil(raw_size / blocksize)

                blocks = []

                for _bnum in range(num_blocks):
                    block = CassetteBlock()
                    block.compressed_size = struct.unpack("I", infile.read(4))[0]
                    blocks.append(block)

                for block in blocks:
                    block.data = infile.read(block.compressed_size)

                infile.read(4)
                infile.close()
            for block in blocks:
                data = zlib.decompress(block.data, wbits=40, bufsize=blocksize)
                info = info + data
            save_data = json.load(BytesIO(info))
        except (OSError, struct.error, ValueError) as err:
            s = str(err)
            self.errorMessage = ('{0}: {1}' if s else '{0}').format(
                err.__class__.__name__, s
            )
            return
        x = json_get_me(save_data, ["party", "player", "custom", "name"], None)
        if type(x) is str:
            self.name = x
        x = json_get_me(save_data, ["saved_datetime"], None)
        if type(x) in (int, float):
            try:
                dt = datetime.fromtimestamp(float(x))
            except OSError:
                pass
            else:
                self.lastsave = "{0:d}-{1:02d}-{2:02d} at {3:02d}:{4:02d}:{5:02d}".format(
                    dt.year, dt.month, dt.day,
                    dt.hour, dt.minute, dt.second
                )
        x = json_get_me(save_data, ["play_time"], None)
        if type(x) in (int, float):
            a = [ 0, 0, 0, int(x * 10) ]
            a[2:4] = divmod(a[3], 10)
            a[1:3] = divmod(a[2], 60)
            a[0:2] = divmod(a[1], 60)
            self.elapsed = "{0:02d}:{1:02d}:{2:02d}.{3:01d}".format(*a)
        x = json_get_me(save_data, ["has_cheated"], None)
        if type(x) is bool:
            self.cheated = "Yes" if x else "No"

    def getName(self) -> str:
        return self.name

    def getCheated(self) -> str:
        return self.cheated

    def getLastSaved(self) -> str:
        return self.lastsave

    def getPlayTime(self) -> str:
        return self.elapsed

def getMetadata(p: Path, save: mobase.ISaveGame) -> Mapping[str, str]:
    if not save.errorMessage:
        return {
            "Character": save.getName(),
            "Last Saved": save.getLastSaved(),
            "Play Time": save.getPlayTime(),
            "Cheated": save.getCheated()
        }
    return {
        "Error loading file:": save.errorMessage
    }

class CassetteBeastsGame(BasicGame):
    Name = "Cassette Beasts Support Plugin"
    Author = "modworkshop"
    Version = "1"
    GameName = "Cassette Beasts"
    GameShortName = "cassette-beasts"
    GameSteamId = 1321440
    GameBinary = "CassetteBeasts.exe"
    GameDataPath = "%USERPROFILE%/AppData/Roaming/CassetteBeasts/mods"
    GameDocumentsDirectory = "%USERPROFILE%/AppData/Roaming/CassetteBeasts"
    GameSavesDirectory = "%GAME_DOCUMENTS%"
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
