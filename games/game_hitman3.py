import os
import shutil
import json
import mobase

from pathlib import Path
from functools import cached_property

from ..basic_game import BasicGame

from PyQt6.QtCore import QDir, QFileInfo


class Hitman3ModDataChecker(mobase.ModDataChecker):
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
        GameSMMPath = self.organizer.managedGame().GameSMMPath
        filetree: mobase.IFileTree = mod.fileTree()
        fixed = False
        if filetree is not None and filetree.exists(GameSMMPath + "/Mods/FOLDERNAME", mobase.IFileTree.DIRECTORY):
            path = mod.absolutePath()
            json_path = os.path.join(path, GameSMMPath + "/Mods/FOLDERNAME/manifest.json")
            mod_data = json.load(open(json_path, encoding="utf-8"))
            modname = mod_data["id"]
            old_path = os.path.join(path, GameSMMPath + "/Mods/FOLDERNAME")
            new_path = os.path.join(path, GameSMMPath + f"/Mods/{modname}")
            self.move_overwrite_merge(old_path, new_path)
            fixed = True
        if not fixed:
            return
        self.needsNameFix = False

    def dataLooksValid(self, filetree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        if filetree.exists("Simple Mod Framework", mobase.IFileTree.DIRECTORY):
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
        GameSMMPath = self.organizer.managedGame().GameSMMPath
        treefixed = 0
        if filetree.exists("manifest.json", mobase.IFileTree.FILE):
            treefixed = self.allMoveTo(filetree, GameSMMPath + "/Mods/FOLDERNAME/")
            if treefixed == 1:
                self.needsNameFix = True
        if treefixed == 0:
            if len(filetree) == 1:
                filetree = filetree.find(filetree[0].path("/"))
                treefixed = self.allMoveTo(filetree, GameSMMPath + "/Mods/FOLDERNAME/")
                if treefixed == 1:
                    self.needsNameFix = True
        if treefixed == 0:
            return None
        return filetree


class Hitman3Game(BasicGame):
    Name = "Hitman 3 Support Plugin"
    Author = "modworkshop"
    Version = "1"
    GameName = "Hitman: World of Assassination"
    GameShortName = "hitman3"
    GameSteamId = 1659040
    GameBinary = "Retail/HITMAN3.exe"
    GameDataPath = "%GAME_PATH%"
    GameSMMPath = "Simple Mod Framework"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = Hitman3ModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        organizer.modList().onModStateChanged(self.update_smm_meta)
        return True

    def update_smm_meta(self, mods: dict[str, mobase.ModState]):
        SMM_Path = os.path.join(self.dataDirectory().absolutePath(), self.GameSMMPath)
        SMM_Config_Json = SMM_Path + "/config.json"
        for key, value in mods.items():
            key = self._organizer.modList().getMod(key)
            tree = key.fileTree()
            subtree = tree.find(self.GameSMMPath + "/Mods", mobase.IFileTree.DIRECTORY)
            if subtree is not None and subtree.isDir():
                for e in subtree:
                    if e is not None and e.isDir():
                        if e.exists("manifest.json", mobase.IFileTree.FILE):
                            json_path = key.absolutePath() + "/" + e.path() + "/manifest.json"
                            mod_data = json.load(open(json_path, encoding="utf-8"))
                            modname = mod_data["id"]
                            if value == 35:
                                with open(SMM_Config_Json, "r") as config_json:
                                    config_json_content = config_json.read()
                                    config_json.close()
                                good_code = '"knownMods": []'
                                if good_code in config_json_content:
                                    bad_code = "{runtimePath:'..\\Runtime',retailPath:'..\\Retail',skipIntro:false,outputToSeparateDirectory:false,loadOrder:[''],modOptions:{},outputConfigToAppDataOnDeploy:true,knownMods:[''],developerMode:false,reportErrors:false}"
                                    config_json_content = bad_code
                                if modname not in config_json_content:
                                    substr = "knownMods:["
                                    config_json_content = config_json_content.replace(substr, substr + "'" + modname + "',")
                                    substr = "loadOrder:["
                                    config_json_content = config_json_content.replace(substr, substr + "'" + modname + "',")
                                    substr = ",],modOptions"
                                    config_json_content = config_json_content.replace(substr, "],modOptions")
                                    substr = ",],developer"
                                    config_json_content = config_json_content.replace(substr, "],developer")
                                    with open(SMM_Config_Json, "w") as config_json:
                                        config_json.write(config_json_content)
                                        config_json.close()
                                return None
                            if value == 33:
                                with open(SMM_Config_Json, "r") as config_json:
                                    config_json_content = config_json.read()
                                    config_json.close()
                                if modname in config_json_content:
                                    config_json_content = config_json_content.replace("'" + modname + "',", "")
                                    config_json_content = config_json_content.replace(",,", ",")
                                    substr = ",],modOptions"
                                    config_json_content = config_json_content.replace(substr, "],modOptions")
                                    substr = ",],developer"
                                    config_json_content = config_json_content.replace(substr, "],developer")
                                    with open(SMM_Config_Json, "w") as config_json:
                                        config_json.write(config_json_content)
                                        config_json.close()
                                return None

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Hitman: World of Assassination",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
            mobase.ExecutableInfo(
                "Launcher",
                QFileInfo(
                    self.gameDirectory(),
                    "Launcher.exe",
                ),
            ),
            mobase.ExecutableInfo(
                "Configure via Simple Mod Framework",
                QFileInfo(
                    self.gameDirectory(),
                    "Simple Mod Framework/Mod Manager/Mod Manager.exe",
                ),
            ),
            mobase.ExecutableInfo(
                "Deploy via Simple Mod Framework",
                QFileInfo(
                    self.gameDirectory(),
                    "Simple Mod Framework/Deploy.exe",
                ),
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

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        modsPath = self.dataDirectory().absolutePath()
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)
        super().initializeProfile(directory, settings)
