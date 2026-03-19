from enum import IntEnum, auto
from functools import cached_property
from pathlib import Path
import os
import re
import shutil

import mobase
from PyQt6.QtCore import QDir, QFileInfo

from ..basic_features import BasicGameSaveGameInfo
from ..basic_game import BasicGame


class Content(IntEnum):
    TEXTURE = auto()
    MESH = auto()
    SCRIPT = auto()
    SOUND = auto()
    STRING = auto()
    CONFIG = auto()


class ZumaModDataContent(mobase.ModDataContent):
    GAMECONTENTS: list[tuple[Content, str, str, bool] | tuple[Content, str, str]] = [
        (Content.TEXTURE, "Textures", ":/MO/gui/content/texture"),
        (Content.MESH, "Meshes", ":/MO/gui/content/mesh"),
        (Content.SCRIPT, "Scripts", ":/MO/gui/content/script"),
        (Content.SOUND, "Sounds", ":/MO/gui/content/sound"),
        (Content.STRING, "Strings", ":/MO/gui/content/string"),
        (Content.CONFIG, "Configs", ":/MO/gui/content/inifile"),
    ]

    def getAllContents(self) -> list[mobase.ModDataContent.Content]:
        return [
            mobase.ModDataContent.Content(id, name, icon, *filter_only)
            for id, name, icon, *filter_only in self.GAMECONTENTS
        ]

    contents = set()

    def walkContent(self, path: str, entry: mobase.FileTreeEntry):
        if entry.isFile():
            match entry.suffix().lower():
                case "texture":
                    self.contents.add(Content.TEXTURE)
                case "model":
                    self.contents.add(Content.MESH)
                case "lua":
                    self.contents.add(Content.SCRIPT)
                case "stream":
                    self.contents.add(Content.SOUND)
                case "txt":
                    self.contents.add(Content.STRING)
                case "json":
                    self.contents.add(Content.CONFIG)
                case _:
                    pass
        return mobase.IFileTree.WalkReturn.CONTINUE

    def getContentsFor(self, filetree: mobase.IFileTree) -> list[int]:
        filetree.walk(self.walkContent, "/")
        return list(self.contents)


class ZumaModDataChecker(mobase.ModDataChecker):
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
        filetree: mobase.IFileTree = mod.fileTree()
        fixed = False
        modname = mod.name()
        if filetree is not None and filetree.exists(
            "mods/FOLDERNAME", mobase.IFileTree.DIRECTORY
        ):
            path = mod.absolutePath()
            old_path = os.path.join(path, "mods/FOLDERNAME")
            new_path = os.path.join(path, f"mods/{modname}")
            self.move_overwrite_merge(old_path, new_path)
            fixed = True
        if not fixed:
            return
        self.needsNameFix = False

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        validFolders = [
            "images",
            "levels",
            "music",
            "sounds",
            "fonts",
            "properties",
            "userdata",
        ]
        validFiles = ["exe"]
        for e in filetree:
            if e.isDir():
                for folder in validFolders:
                    if filetree.exists(folder, mobase.IFileTree.DIRECTORY):
                        return mobase.ModDataChecker.VALID
            elif e.isFile():
                for ext in validFiles:
                    if e.suffix().lower() == ext:
                        return mobase.ModDataChecker.VALID
            else:
                pass
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
        GameLevelsPath = self.organizer.managedGame().GameLevelsPath
        validFolders = [
            "images",
            "levels",
            "music",
            "sounds",
            "fonts",
            "properties",
            "userdata",
        ]
        entriesToMove: list[mobase.FileTreeEntry] = []
        treefixed = 0
        if filetree.exists("map.txt", mobase.IFileTree.FILE):
            treefixed = self.allMoveTo(filetree, GameLevelsPath + "/FOLDERNAME/")
            if treefixed == 1:
                self.needsNameFix = True
        elif self.fileExistsInNextSubDir(filetree, "map.txt"):
            filetree.move(filetree[0], GameLevelsPath, mobase.IFileTree.MERGE)
            treefixed = 1
        else:
            moveonce = 0
            for branch in filetree:
                if branch is not None and branch.isDir():
                    for entry in branch:
                        for folder in validFolders:
                            if entry is not None and entry.name() == folder:
                                moveonce = 1
            if moveonce == 1:
                for branch in filetree:
                    if branch is not None and branch.isDir():
                        for entry in branch:
                            entriesToMove.append(entry)
        if entriesToMove is not None:
            for e in entriesToMove:
                filetree.move(e, "", mobase.IFileTree.MERGE)
                treefixed = 1
        for branch in filetree:
            if branch is not None and branch.isDir():
                if len(branch) == 0:
                    filetree.remove(branch)
        if treefixed == 0:
            return None
        return filetree


PROGRAM_DATA = str(os.getenv("ProgramData"))


class ZumaGame(BasicGame, mobase.IPluginFileMapper):
    Name = "Zuma Deluxe Support Plugin"
    Author = "modworkshop"
    Version = "1"
    GameName = "Zuma Deluxe"
    GameShortName = "zuma"
    GameSteamId = 3330
    GameBinary = "Zuma.exe"
    GameDataPath = "%GAME_PATH%"
    GameLevelsPath = "levels"
    GameLevelsXml = "levels/levels.xml"
    ProfileLevelsXml = "levels.xml"
    GameDocumentsDirectory = PROGRAM_DATA + "/Steam/Zuma/userdata"
    GameSaveExtension = "sav"

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = ZumaModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        self._register_feature(ZumaModDataContent())
        self._register_feature(BasicGameSaveGameInfo())
        organizer.modList().onModStateChanged(self.update_levels)
        return True

    def update_levels(self, mods: dict[str, mobase.ModState]):
        profile_levels_path = (
            self._organizer.profilePath() + "/" + self.ProfileLevelsXml
        )
        game_levels_path = os.path.join(
            self.dataDirectory().absolutePath(), self.GameLevelsXml
        )
        for key, value in mods.items():
            key = self._organizer.modList().getMod(key)
            tree = key.fileTree()
            if tree.exists("levels/levels.xml", mobase.IFileTree.FILE):
                levels_txt_path = os.path.join(key.absolutePath(), "levels/levels.xml")
                profile_levels_path = (
                    self._organizer.profilePath() + "/" + self.ProfileLevelsXml
                )
                if value == 35:
                    with open(levels_txt_path, "r") as levels_txt:
                        levels_txt_content = levels_txt.read()
                        levels_txt.close()
                    with open(profile_levels_path, "w") as profile_levels:
                        profile_levels.write(levels_txt_content)
                        profile_levels.close()
                if value == 33:
                    with open(game_levels_path, "r") as game_levels:
                        game_levels_content = game_levels.read()
                        game_levels.close()
                    with open(profile_levels_path, "w") as profile_levels:
                        profile_levels.write(game_levels_content)
                        profile_levels.close()
        for key, value in mods.items():
            key = self._organizer.modList().getMod(key)
            map_txt_path = os.path.join(key.absolutePath(), "levels/map.txt")
            tree = key.fileTree()
            if tree.exists("levels/map.txt", mobase.IFileTree.FILE):
                with open(map_txt_path, "r") as map_txt:
                    map_txt_content = map_txt.read()
                    map_txt.close()
                graphics_pattern = r"(?=<Graphics)(.*?)(?<=Graphics>)"
                levels_pattern = r"(?=<Level)(.*?)(?<=\/>)"
                id_pattern = r'(?<=id=")(.*?)(?=")'
                graphics_tag = re.findall(graphics_pattern, map_txt_content, re.DOTALL)
                levels_tag = re.findall(levels_pattern, map_txt_content, re.DOTALL)
                id_name = re.findall(id_pattern, map_txt_content, re.DOTALL)
                with open(profile_levels_path, "r+") as profile_levels:
                    profile_levels_content = profile_levels.read()
                    profile_levels.seek(0)
                    if value == 35:
                        insert_graphics_string = ""
                        for graphic in graphics_tag:
                            insert_graphics_string += "\n\n" + graphic
                        insert_graphics_string += "\n\n<Graphics"
                        profile_levels_content = profile_levels_content.replace(
                            "\n\n<Graphics", insert_graphics_string, 1
                        )
                        insert_level_string = ""
                        for level in levels_tag:
                            insert_level_string = "\n" + level
                        insert_level_string += "\n<Level grap"
                        profile_levels_content = profile_levels_content.replace(
                            "\n<Level grap", insert_level_string, 1
                        )
                        for id in id_name:
                            substr = 'stage1 = "'
                            insertstr = substr + id + ","
                            profile_levels_content = profile_levels_content.replace(
                                substr, insertstr, 1
                            )
                            substr = 'diffi1 = "'
                            insertstr = substr + "lvl42,"
                            profile_levels_content = profile_levels_content.replace(
                                substr, insertstr, 1
                            )
                    elif value == 33:
                        for graphic in graphics_tag:
                            profile_levels_content = profile_levels_content.replace(
                                "\n\n" + graphic, ""
                            )
                        for level in levels_tag:
                            profile_levels_content = profile_levels_content.replace(
                                "\n" + level, ""
                            )
                        for id in id_name:
                            profile_levels_content = profile_levels_content.replace(
                                id + ",", ""
                            )
                            profile_levels_content = profile_levels_content.replace(
                                'diffi1 = "lvl42,', 'diffi1 = "'
                            )
                    else:
                        return
                    profile_levels.truncate(0)
                    profile_levels.write(profile_levels_content)
                    profile_levels.close()

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Zuma Deluxe",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
            mobase.ExecutableInfo(
                "Delta Patcher", QFileInfo(self.gameDirectory(), "DeltaPatcher.exe")
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

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        modsPath = self.dataDirectory().absolutePath()
        profile_levels_path = directory.absolutePath() + "/" + self.ProfileLevelsXml
        game_levels_path = os.path.join(
            self.dataDirectory().absolutePath(), self.GameLevelsXml
        )
        if (
            not os.path.exists(profile_levels_path)
            or os.path.getsize(profile_levels_path) == 0
        ):
            with open(game_levels_path, "r") as game_levels:
                profile_levels_content = game_levels.read()
                game_levels.close()
            with open(profile_levels_path, "w") as profile_levels:
                profile_levels.write(profile_levels_content)
                profile_levels.close()
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)
        super().initializeProfile(directory, settings)

    def mappings(self) -> list[mobase.Mapping]:
        return [
            mobase.Mapping(
                self._organizer.profilePath() + "/" + self.ProfileLevelsXml,
                self.gameDirectory().absolutePath() + "/" + self.GameLevelsXml,
                False,
                False,
            ),
        ]
