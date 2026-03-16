from enum import IntEnum, auto
from functools import cached_property
from pathlib import Path
import os
import shutil

import mobase
from PyQt6.QtCore import QDir, QFileInfo

from ..basic_game import BasicGame

class Content(IntEnum):
    TEXTURE = auto()
    MESH = auto()
    SCRIPT = auto()
    SOUND = auto()
    STRING = auto()
    CONFIG = auto()


class Payday1ModDataContent(mobase.ModDataContent):
    GAMECONTENTS: list[tuple[Content, str, str, bool] | tuple[Content, str, str]] = [
        (Content.TEXTURE, "Textures", ":/MO/gui/content/texture"),
        (Content.MESH, "Meshes", ":/MO/gui/content/mesh"),
        (Content.SCRIPT, "Scripts", ":/MO/gui/content/script"),
        (Content.SOUND, "Sounds", ":/MO/gui/content/sound"),
        (Content.STRING, "Strings", ":/MO/gui/content/string"),
        (Content.CONFIG, "Configs", ":/MO/gui/content/inifile"),
    ]

    def getAllContents(self) -> list[mobase.ModDataContent.Content]:
        return [mobase.ModDataContent.Content(id, name, icon, *filter_only) for id, name, icon, *filter_only in self.GAMECONTENTS]

    contents = set()

    def walkContent(self, path: str, entry: mobase.FileTreeEntry):
        if entry.isFile():
            match entry.suffix().casefold():
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


class Payday1ModDataChecker(mobase.ModDataChecker):
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
        if filetree is not None and filetree.exists("mods/FOLDERNAME", mobase.IFileTree.DIRECTORY):
            path = mod.absolutePath()
            old_path = os.path.join(path, "mods/FOLDERNAME")
            new_path = os.path.join(path, f"mods/{modname}")
            self.move_overwrite_merge(old_path, new_path)
            fixed = True
        elif filetree is not None and filetree.exists("assets/mod_overrides/FOLDERNAME/", mobase.IFileTree.DIRECTORY):
            path = mod.absolutePath()
            old_path = os.path.join(path, "assets/mod_overrides/FOLDERNAME")
            new_path = os.path.join(path, f"assets/mod_overrides/{modname}")
            self.move_overwrite_merge(old_path, new_path)
            fixed = True
        elif filetree is not None and filetree.exists("maps/FOLDERNAME", mobase.IFileTree.DIRECTORY):
            path = mod.absolutePath()
            old_path = os.path.join(path, "maps/FOLDERNAME")
            new_path = os.path.join(path, f"maps/{modname}")
            self.move_overwrite_merge(old_path, new_path)
            fixed = True
        if not fixed:
            return
        self.needsNameFix = False

    def dataLooksValid(self, filetree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        if filetree.exists("assets/mod_overrides", mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        if filetree.exists("mods", mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        if filetree.exists("maps", mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        for e in filetree:
            if e is not None and e.suffix().casefold() == "dll":
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
        treefixed = 0
        if filetree.exists("mod.txt", mobase.IFileTree.FILE):
            treefixed = self.allMoveTo(filetree, "mods/FOLDERNAME/")
            if treefixed == 1:
                self.needsNameFix = True
        elif self.fileExistsInNextSubDir(filetree, "mod.txt"):
            filetree.move(filetree[0], "mods/", mobase.IFileTree.MERGE)
            treefixed = 1
        elif self.fileExistsInNextSubDir(filetree, "main.xml"):
            if self.fileExistsInNextSubDir(filetree, "levels"):
                filetree.move(filetree[0], "maps/", mobase.IFileTree.MERGE)
                treefixed = 1
            else:
                filetree.move(filetree[0], "assets/mod_overrides/", mobase.IFileTree.MERGE)
                treefixed = 1
        elif filetree.exists("main.xml", mobase.IFileTree.FILE):
            if filetree.exists("levels", mobase.IFileTree.DIRECTORY):
                treefixed = self.move_overwrite_merge(filetree, "maps/FOLDERNAME")
                if treefixed == 1:
                    self.needsNameFix = True
            else:
                treefixed = self.allMoveTo(filetree, "assets/mod_overrides/FOLDERNAME/")
                if treefixed == 1:
                    self.needsNameFix = True
        else:
            if filetree[0][0].exists("mod.txt", mobase.IFileTree.FILE):
                filetree.move(filetree[0][0], filetree[0].path("/"), mobase.IFileTree.REPLACE)
                filetree.move(filetree[0], "mods/", mobase.IFileTree.MERGE)
                treefixed = 1
            elif filetree[0][0].exists("main.xml", mobase.IFileTree.FILE):
                if filetree.exists("levels", mobase.IFileTree.DIRECTORY):
                    filetree.move(filetree[0][0], filetree[0].path("/"), mobase.IFileTree.REPLACE)
                    filetree.move(filetree[0], "maps/", mobase.IFileTree.MERGE)
                    treefixed = 1
                else:
                    filetree.move(filetree[0][0], filetree[0].path("/"), mobase.IFileTree.REPLACE)
                    filetree.move(filetree[0], "assets/mod_overrides/", mobase.IFileTree.MERGE)
                    treefixed = 1
        if treefixed == 0:
            if len(filetree) == 1:
                filetree.move(filetree[0], "assets/mod_overrides/", mobase.IFileTree.MERGE)
                treefixed = 1
            else:
                for e in filetree:
                    if e is not None and e.path("/").count("/") == 0:
                        filetree.move(e, "assets/mod_overrides/FOLDERNAME/", mobase.IFileTree.MERGE)
                        treefixed = 1
                        self.needsNameFix = True
        if treefixed == 0:
            return None
        return filetree


class Payday1Game(BasicGame):
    Name = "Payday 1 Support Plugin"
    Author = "modworkshop"
    Version = "1"
    GameName = "Payday: The Heist"
    GameShortName = "pdth"
    GameSteamId = 24240
    GameBinary = "payday_win32_release.exe"
    GameDataPath = "%GAME_PATH%"
    GameDocumentsDirectory = "%USERPROFILE%/AppData/Local/PAYDAY"
    _forced_libraries = ["IPHLPAPI.dll", "WSOCK32.dll"]

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = Payday1ModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        self._register_feature(Payday1ModDataContent())
        organizer.modList().onModStateChanged(self.dll_copy)
        return True

    def dll_copy(
        self, mods: dict[str, mobase.ModState]
    ):

        game_path = self.dataDirectory().absolutePath() + "/"

        for key, value in mods.items():
            key = self._organizer.modList().getMod(key)
            tree = key.fileTree()
            for e in tree:
                if e is not None and e.name() in self._forced_libraries:
                    #add file
                    file_path_source = key.absolutePath() + "/" + e.path()
                    file_path_target = game_path + e.name()
                    if value == 35:
                        shutil.copyfile(file_path_source, file_path_target)
                    #remove file
                    if value == 33:
                        if os.path.exists(file_path_target):
                            os.remove(file_path_target)

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Payday: The Heist",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
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
        return ["renderer_settings.xml"]

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        modsPath = self.dataDirectory().absolutePath()
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)
        super().initializeProfile(directory, settings)
