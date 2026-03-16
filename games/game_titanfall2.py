from enum import IntEnum, auto
from functools import cached_property
import json
from pathlib import Path
import os
import shutil

import mobase
from PyQt6.QtCore import QDir, QFileInfo

from ..basic_game import BasicGame


class Content(IntEnum):
    MATERIAL = auto()
    TEXTURE = auto()
    MODELS = auto()
    SCRIPT = auto()
    CONFIG = auto()
    VIDEO = auto()
    AUDIO = auto()
    STARPAK = auto()


class Titanfall2ModDataContent(mobase.ModDataContent):
    GAMECONTENTS: list[tuple[Content, str, str, bool] | tuple[Content, str, str]] = [
        (Content.MATERIAL, "Materials", ":/MO/gui/content/interface"),
        (Content.TEXTURE, "Textures", ":/MO/gui/content/texture"),
        (Content.MODELS, "Models", ":/MO/gui/content/mesh"),
        (Content.SCRIPT, "Scripts", ":/MO/gui/content/script"),
        (Content.CONFIG, "Configs", ":/MO/gui/content/inifile"),
        (Content.VIDEO, "Video", ":/MO/gui/content/modgroup"),
        (Content.AUDIO, "Audio", ":/MO/gui/content/sound"),
        (Content.STARPAK, "Starpak", ":/MO/gui/content/bsa"),
    ]

    def getAllContents(self) -> list[mobase.ModDataContent.Content]:
        return [
            mobase.ModDataContent.Content(id, name, icon, *filter_only)
            for id, name, icon, *filter_only in self.GAMECONTENTS
        ]

    contents = set()

    def walkContent(self, path: str, entry: mobase.FileTreeEntry):
        if entry.isFile():
            match entry.suffix().casefold():
                case "vmt":
                    self.contents.add(Content.MATERIAL)
                case "vtf":
                    self.contents.add(Content.TEXTURE)
                case "mdl":
                    self.contents.add(Content.MODELS)
                case "nut":
                    self.contents.add(Content.SCRIPT)
                case "txt":
                    self.contents.add(Content.CONFIG)
                case "bik":
                    self.contents.add(Content.VIDEO)
                case "wav":
                    self.contents.add(Content.AUDIO)
                case "rpak" | "starmap" | "starpak":
                    self.contents.add(Content.STARPAK)
                case _:
                    pass
        return mobase.IFileTree.WalkReturn.CONTINUE

    def getContentsFor(self, filetree: mobase.IFileTree) -> list[int]:
        filetree.walk(self.walkContent, "/")
        return list(self.contents)


class Titanfall2ModDataChecker(mobase.ModDataChecker):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self.organizer: mobase.IOrganizer = organizer
        self.organizer.modList().onModInstalled(self._Fix_Installed_Mod)
        self.needsNameFix = False

    def move_overwrite_merge(self, source, destination):
        if not os.path.exists(destination):
            shutil.move(source, destination)
            return
        if os.path.isfile(source):
            os.replace(source, destination)
            return
        for item in os.listdir(source):
            s_item = os.path.join(source, item)
            d_item = os.path.join(destination, item)
            self.move_overwrite_merge(s_item, d_item)
        os.rmdir(source)

    def _Fix_Installed_Mod(self, mod: mobase.IModInterface):
        if not self.needsNameFix:
            return
        northstarModPath = self.organizer.managedGame().GameNorthstarPath + "/"
        filetree: mobase.IFileTree = mod.fileTree()
        fixed = False
        modname = mod.name()
        if filetree is not None and filetree.exists(
            northstarModPath + "FOLDERNAME", mobase.IFileTree.DIRECTORY
        ):
            path = mod.absolutePath()
            json_path = os.path.join(path, northstarModPath + "FOLDERNAME/mod.json")
            with open(json_path, "r") as json_data:
                mod_data = json.load(json_data)
                json_data.close()
            modname = mod_data["name"]
            old_path = os.path.join(path, northstarModPath + "FOLDERNAME")
            new_path = os.path.join(path, northstarModPath + f"{modname}")
            self.move_overwrite_merge(old_path, new_path)
            fixed = True
        elif filetree is not None and filetree.exists(
            northstarModPath + "FOLDERNAME_NAME", mobase.IFileTree.DIRECTORY
        ):
            path = mod.absolutePath()
            old_path = os.path.join(path, northstarModPath + "FOLDERNAME_NAME")
            new_path = os.path.join(path, northstarModPath + f"{modname}")
            self.move_overwrite_merge(old_path, new_path)
            fixed = True
        if not fixed:
            return
        self.needsNameFix = False

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        if filetree.exists("R2Northstar", mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.FIXABLE

    def fileExistsInNextSubDir(self, filetree: mobase.IFileTree, name: str):
        for branch in filetree:
            if branch is not None and branch.isDir():
                for e in branch:
                    if e is not None and e.name() == name:
                        return True
        return False

    def allMoveTo(self, filetree: mobase.IFileTree, toMoveTo: str):
        entriesToMove: list[mobase.FileTreeEntry] = []
        retVal = 0
        for e in filetree:
            if e is not None:
                entriesToMove.append(e)
        for e in entriesToMove:
            filetree.move(e, toMoveTo, mobase.IFileTree.MERGE)
            retVal = 1
        return retVal

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        northstarModPath = self.organizer.managedGame().GameNorthstarPath + "/"
        treefixed = 0
        if filetree.exists("mod.json", mobase.IFileTree.FILE):
            treefixed = self.allMoveTo(filetree, northstarModPath + "FOLDERNAME/")
            if treefixed == 1:
                self.needsNameFix = True
        elif self.fileExistsInNextSubDir(filetree, "mod.json"):
            filetree.move(filetree[0], northstarModPath, mobase.IFileTree.MERGE)
            treefixed = 1
        else:
            try:
                if filetree[0][0].exists("mod.json", mobase.IFileTree.FILE):
                    filetree.move(
                        filetree[0][0], filetree[0].path("/"), mobase.IFileTree.REPLACE
                    )
                    filetree.move(filetree[0], northstarModPath, mobase.IFileTree.MERGE)
                    treefixed = 1
            except TypeError:
                pass
        if treefixed == 0:
            if len(filetree) == 1 and filetree[0].isDir:
                filetree.move(filetree[0], northstarModPath, mobase.IFileTree.MERGE)
                treefixed = 1
            else:
                for e in filetree:
                    if e is not None and e.path("/").count("/") == 0:
                        filetree.move(
                            e,
                            northstarModPath + "FOLDERNAME_NAME/",
                            mobase.IFileTree.MERGE,
                        )
                        treefixed = 1
                        self.needsNameFix = True
        if treefixed == 0:
            return None
        return filetree


class Titanfall2Game(BasicGame):
    Name = "Titanfall 2 Support Plugin"
    Author = "modworkshop"
    Version = "1"
    GameName = "Titanfall 2"
    GameShortName = "titanfall-2"
    GameSteamId = 1237970
    GameBinary = "Titanfall2.exe"
    GameDataPath = "%GAME_PATH%"
    GameNorthstarPath = "R2Northstar/mods"
    NorthstarModJson = "enabledmods.json"
    GameDocumentsDirectory = "%USERPROFILE%/Documents/Respawn/Titanfall2/profile"
    GameSavesDirectory = "%USERPROFILE%/Documents/Respawn/Titanfall2/profile/savegames/"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = Titanfall2ModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        self._register_feature(Titanfall2ModDataContent())
        organizer.modList().onModStateChanged(self.update_enable_mods_json)
        return True

    def update_enable_mods_json(self, mods: dict[str, mobase.ModState]):
        Northstar_Config_Json = (
            self._organizer.profilePath() + "/" + self.NorthstarModJson
        )
        with open(Northstar_Config_Json, "r", encoding="utf-8") as f:
            Northstar = json.load(f)
        for key, value in mods.items():
            key = self._organizer.modList().getMod(key)
            tree = key.fileTree()
            subtree = tree.find("R2Northstar/mods", mobase.IFileTree.DIRECTORY)
            if subtree is not None and subtree.isDir():
                for e in subtree:
                    if e is not None and e.isDir():
                        if e.exists("mod.json", mobase.IFileTree.FILE):
                            json_path = (
                                key.absolutePath() + "/" + e.path() + "/mod.json"
                            )
                            with open(json_path, "r", encoding="utf-8") as f:
                                mod_data = json.load(f)
                            modname = mod_data["Name"]
                            if "Version" not in mod_data:
                                modversion = "0.0.0"
                            else:
                                modversion = mod_data["Version"]
                            if value == 35 and modname not in Northstar:
                                Northstar[modname] = {modversion: True}
                            if value == 33 and modname in Northstar:
                                Northstar = Northstar.pop(modname)
                            with open(
                                Northstar_Config_Json, "w", encoding="utf-8"
                            ) as f:
                                json.dump(Northstar, f, ensure_ascii=False, indent=4)

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Titanfall 2",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
            mobase.ExecutableInfo(
                "Northstar", QFileInfo(self.gameDirectory(), "NorthstarLauncher.exe")
            ),
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
        tree: mobase.IFileTree | mobase.FileTreeEntry | None = (
            self._organizer.virtualFileTree()
        )
        if type(tree) is not mobase.IFileTree:
            return efls
        for e in tree:
            relpath = e.pathFrom(tree)
            if relpath and e.hasSuffix("dll") and relpath not in self._base_dlls:
                libs.add(relpath)
        exes = self.executables()
        efls = efls + [
            mobase.ExecutableForcedLoadSetting(
                exe.binary().fileName(), lib
            ).withEnabled(True)
            for lib in libs
            for exe in exes
        ]
        return efls

    def northstarDirectory(self) -> QDir:
        return QDir(self.gameDirectory().absolutePath() + self.GameNorthstarPath)

    def iniFiles(self):
        return ["profile.cfg"]

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        northstar_json_path = directory.absolutePath() + "/" + self.NorthstarModJson
        northstar_json_game_path = (
            self.gameDirectory().absolutePath()
            + "/R2Northstar/"
            + self.NorthstarModJson
        )
        blank_mod_json = '{"Version": 1,"Northstar.Client": {"1.31.6": true},"Northstar.CustomServers": {"1.31.6": true},"Northstar.Custom": {"1.31.6": true}}'
        if (
            not os.path.exists(northstar_json_path)
            or os.path.getsize(northstar_json_path) == 0
        ):
            if os.path.exists(northstar_json_game_path):
                with open(northstar_json_game_path, "r") as game_json:
                    game_json_content = game_json.read()
                    game_json.close()
                with open(northstar_json_path, "w") as northstar_json:
                    northstar_json.write(game_json_content)
                    northstar_json.close()
            else:
                with open(northstar_json_path, "w") as northstar_json:
                    northstar_json.write(blank_mod_json)
                    northstar_json.close()
        modsPath = os.path.join(
            self.dataDirectory().absolutePath(), self.GameNorthstarPath
        )
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)
        super().initializeProfile(directory, settings)

    def mappings(self) -> list[mobase.Mapping]:
        return [
            mobase.Mapping(
                self._organizer.profilePath() + "/" + self.NorthstarModJson,
                self.gameDirectory().absolutePath()
                + "/R2Northstar/"
                + self.NorthstarModJson,
                False,
                False,
            ),
        ]
