import json
import os
import shutil
from enum import IntEnum, auto
from functools import cached_property
from pathlib import Path

from PyQt6.QtCore import QDir, QFileInfo

import mobase

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
    content: list[int] = []
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

    def walkContent(self, path: str, entry: mobase.FileTreeEntry):
        if entry.isFile():
            match entry.suffix().casefold():
                case "vmt":
                    self.content.append(Content.MATERIAL)
                case "vtf":
                    self.content.append(Content.TEXTURE)
                case "mdl":
                    self.content.append(Content.MODELS)
                case "nut":
                    self.content.append(Content.SCRIPT)
                case "txt":
                    self.content.append(Content.CONFIG)
                case "bik":
                    self.content.append(Content.VIDEO)
                case "wav":
                    self.content.append(Content.AUDIO)
                case "rpak" | "starmap" | "starpak":
                    self.content.append(Content.STARPAK)
                case _:
                    pass
        return mobase.IFileTree.WalkReturn.CONTINUE

    def getContentsFor(self, filetree: mobase.IFileTree) -> list[int]:
        filetree.walk(self.walkContent, "/")
        return list(self.content)


class Titanfall2ModDataChecker(mobase.ModDataChecker):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self.organizer: mobase.IOrganizer = organizer
        self.organizer.modList().onModInstalled(self._Fix_Installed_Mod)
        self.needsNameFix = False

    def move_overwrite_merge(self, source: str, destination: str):
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
        GameNorthstarPath = (
            getattr(self.organizer.managedGame(), "GameNorthstarPath", "") + "/"
        )
        filetree: mobase.IFileTree = mod.fileTree()
        fixed = False
        modname = mod.name()
        if filetree.exists(
            GameNorthstarPath + "FOLDERNAME", mobase.IFileTree.DIRECTORY
        ):
            path = mod.absolutePath()
            json_path = os.path.join(path, GameNorthstarPath + "FOLDERNAME/mod.json")
            with open(json_path, "r") as json_data:
                mod_data = json.load(json_data)
                json_data.close()
            modname = mod_data["name"]
            old_path = os.path.join(path, GameNorthstarPath + "FOLDERNAME")
            new_path = os.path.join(path, GameNorthstarPath + f"{modname}")
            self.move_overwrite_merge(old_path, new_path)
            fixed = True
        elif filetree.exists(
            GameNorthstarPath + "FOLDERNAME_NAME", mobase.IFileTree.DIRECTORY
        ):
            path = mod.absolutePath()
            old_path = os.path.join(path, GameNorthstarPath + "FOLDERNAME_NAME")
            new_path = os.path.join(path, GameNorthstarPath + f"{modname}")
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
            if isinstance(branch, mobase.IFileTree):
                for e in branch:
                    if e.name() == name:
                        return True
        return False

    def first_tree(self, filetree: mobase.IFileTree) -> mobase.IFileTree | None:
        for e in filetree:
            if isinstance(e, mobase.IFileTree) and e.isDir():
                return e
        return None

    def allMoveTo(self, filetree: mobase.IFileTree, toMoveTo: str):
        entriesToMove: list[mobase.FileTreeEntry] = []
        retVal = 0
        for e in filetree:
            entriesToMove.append(e)
        for e in entriesToMove:
            filetree.move(e, toMoveTo, mobase.IFileTree.MERGE)
            retVal = 1
        return retVal

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree | None:
        GameNorthstarPath = (
            getattr(self.organizer.managedGame(), "GameNorthstarPath", "") + "/"
        )
        treefixed = 0
        firsttreelayer: mobase.IFileTree | None = self.first_tree(filetree)
        if firsttreelayer is not None:
            secondtreelayer: mobase.IFileTree | None = self.first_tree(firsttreelayer)
            if filetree.exists("mod.json", mobase.IFileTree.FILE):
                treefixed = self.allMoveTo(filetree, GameNorthstarPath + "FOLDERNAME/")
                if treefixed == 1:
                    self.needsNameFix = True
            elif self.fileExistsInNextSubDir(filetree, "mod.json"):
                filetree.move(firsttreelayer, GameNorthstarPath, mobase.IFileTree.MERGE)
                treefixed = 1
                if secondtreelayer is not None:
                    if secondtreelayer.exists("mod.json", mobase.IFileTree.FILE):
                        filetree.move(
                            secondtreelayer,
                            firsttreelayer.path("/"),
                            mobase.IFileTree.REPLACE,
                        )
                        filetree.move(
                            firsttreelayer, GameNorthstarPath, mobase.IFileTree.MERGE
                        )
                        treefixed = 1
                    elif len(filetree) == 1:
                        filetree.move(
                            firsttreelayer, GameNorthstarPath, mobase.IFileTree.MERGE
                        )
                        treefixed = 1
                    else:
                        for e in filetree:
                            if e.path("/").count("/") == 0:
                                filetree.move(
                                    e,
                                    GameNorthstarPath + "FOLDERNAME_NAME/",
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
            if isinstance(subtree, mobase.IFileTree):
                for e in subtree:
                    if isinstance(e, mobase.IFileTree):
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
