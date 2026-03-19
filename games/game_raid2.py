import os
import shutil
import mobase

from enum import IntEnum, auto
from pathlib import Path
from functools import cached_property

from ..basic_game import BasicGame

from PyQt6.QtCore import QDir, QFileInfo


class Content(IntEnum):
    TEXTURE = auto()
    MESH = auto()
    SCRIPT = auto()
    SOUND = auto()
    STRING = auto()
    CONFIG = auto()


class RaidWW2ModDataContent(mobase.ModDataContent):
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


class RaidWW2ModDataChecker(mobase.ModDataChecker):
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
        if filetree is not None and filetree.exists("FOLDERNAME", mobase.IFileTree.DIRECTORY):
            path = mod.absolutePath()
            old_path = os.path.join(path, "FOLDERNAME")
            new_path = os.path.join(path, f"{modname}")
            self.move_overwrite_merge(old_path, new_path)
            fixed = True
        if not fixed:
            return
        self.needsNameFix = False

    def dataLooksValid(self, filetree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        if len(filetree) == 1:
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
        treefixed = self.allMoveTo(filetree, "FOLDERNAME/")
        if treefixed == 1:
            self.needsNameFix = True
        return filetree


class RaidWW2Game(BasicGame):
    Name = "RAID World War II Support Plugin"
    Author = "modworkshop"
    Version = "1"
    GameName = "RAID World War II"
    GameShortName = "raidww2"
    GameSteamId = 414740
    GameBinary = "raid_win64_release.exe"
    GameDataPath = "mods"
    GameDocumentsDirectory = "%LOCALAPPDATA%/RAID WW2"
    _forced_libraries = ["IPHLPAPI.dll", "WSOCK32.dll"]

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = RaidWW2ModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        self._register_feature(RaidWW2ModDataContent())
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
                "Raid: World War II",
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
