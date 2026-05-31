import json
import os
import shutil
from functools import cached_property
from pathlib import Path

from PyQt6.QtCore import QDir, QFileInfo

import mobase

from ..basic_game import BasicGame


class Hitman3ModDataChecker(mobase.ModDataChecker):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self.organizer: mobase.IOrganizer = organizer
        self.organizer.modList().onModInstalled(self.fixInstalledMod)
        self.needsNameFix = False

    def moveOverwriteMerge(self, source: str, destination: str):
        if not os.path.exists(destination):
            shutil.move(source, destination)
            return
        if os.path.isfile(source):
            os.replace(source, destination)
            return
        for item in os.listdir(source):
            s_item = os.path.join(source, item)
            d_item = os.path.join(destination, item)
            self.moveOverwriteMerge(s_item, d_item)
        os.rmdir(source)

    def readManifestId(self, manifest_path: str) -> str | None:
        try:
            with open(manifest_path, encoding="utf-8") as manifest_file:
                mod_data = json.load(manifest_file)
        except (OSError, json.JSONDecodeError):
            return None

        mod_id = mod_data.get("id")
        if isinstance(mod_id, str) and mod_id:
            return mod_id
        return None

    def fixInstalledMod(self, mod: mobase.IModInterface):
        if not self.needsNameFix:
            return
        GameSMMPath = getattr(self.organizer.managedGame(), "GameSMMPath", "")
        filetree: mobase.IFileTree = mod.fileTree()
        fixed = False
        foldername_path = GameSMMPath + "/Mods/FOLDERNAME"
        if filetree.exists(foldername_path, mobase.IFileTree.DIRECTORY):
            path = mod.absolutePath()
            json_path = os.path.join(path, foldername_path, "manifest.json")
            modname = self.readManifestId(json_path)
            if not modname:
                return
            old_path = os.path.join(path, foldername_path)
            new_path = os.path.join(path, GameSMMPath, "Mods", modname)
            self.moveOverwriteMerge(old_path, new_path)
            fixed = True
        if not fixed:
            return
        self.needsNameFix = False

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        validList = {"simple mod framework"}
        for e in filetree:
            if isinstance(e, mobase.IFileTree) and e.isDir():
                if e.name().casefold() not in validList:
                    return mobase.ModDataChecker.FIXABLE
        if filetree.exists("Simple Mod Framework", mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.FIXABLE

    def allMoveTo(
        self, sourcetree: mobase.IFileTree, targettree: mobase.IFileTree, toMoveTo: str
    ) -> bool:
        entriesToMove: list[mobase.FileTreeEntry] = []
        for e in sourcetree:
            entriesToMove.append(e)
        for e in entriesToMove:
            targettree.move(e, toMoveTo, mobase.IFileTree.MERGE)
        if sourcetree is not targettree:
            targettree.remove(sourcetree)
        return bool(entriesToMove)

    def firstTree(self, filetree: mobase.IFileTree) -> mobase.IFileTree | None:
        for e in filetree:
            if isinstance(e, mobase.IFileTree) and e.isDir():
                return e
        return None

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree | None:
        GameSMMPath = getattr(self.organizer.managedGame(), "GameSMMPath", "")

        if filetree.exists("manifest.json", mobase.IFileTree.FILE):
            if self.allMoveTo(
                filetree,
                filetree,
                GameSMMPath + "/Mods/FOLDERNAME/",
            ):
                self.needsNameFix = True

        elif len(filetree) == 1:
            firsttreelayer = self.firstTree(filetree)

            if firsttreelayer is not None and firsttreelayer.exists(
                "manifest.json", mobase.IFileTree.FILE
            ):
                if self.allMoveTo(
                    firsttreelayer,
                    filetree,
                    GameSMMPath + "/Mods/FOLDERNAME/",
                ):
                    self.needsNameFix = True

        return filetree


class Hitman3Game(BasicGame):
    Name = "Hitman 3 Support Plugin"
    Author = "ModWorkshop"
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
        organizer.modList().onModStateChanged(self.updateSmmMeta)
        return True

    def updateSmmMeta(self, mods: dict[str, mobase.ModState]):
        SMM_Path = os.path.join(self.dataDirectory().absolutePath(), self.GameSMMPath)
        SMM_Config_Json = os.path.join(SMM_Path, "config.json")

        if not os.path.exists(SMM_Config_Json):
            return None

        for key, value in mods.items():
            mod = self._organizer.modList().getMod(key)
            tree = mod.fileTree()
            subtree = tree.find(self.GameSMMPath + "/Mods", mobase.IFileTree.DIRECTORY)
            if not isinstance(subtree, mobase.IFileTree):
                continue

            for e in subtree:
                if not isinstance(e, mobase.IFileTree):
                    continue
                if not e.exists("manifest.json", mobase.IFileTree.FILE):
                    continue

                json_path = os.path.join(mod.absolutePath(), e.path(), "manifest.json")
                try:
                    with open(json_path, encoding="utf-8") as manifest_file:
                        mod_data = json.load(manifest_file)
                except (OSError, json.JSONDecodeError):
                    continue

                modname = mod_data.get("id")
                if not isinstance(modname, str) or not modname:
                    continue

                try:
                    with open(SMM_Config_Json, "r", encoding="utf-8") as config_json:
                        config_json_content = config_json.read()
                except OSError:
                    return None

                good_code = '"knownMods": []'
                if good_code in config_json_content:
                    config_json_content = "{runtimePath:'..\\Runtime',retailPath:'..\\Retail',skipIntro:false,outputToSeparateDirectory:false,loadOrder:[''],modOptions:{},outputConfigToAppDataOnDeploy:true,knownMods:[''],developerMode:false,reportErrors:false}"

                quoted_modname = "'" + modname + "'"
                changed = False
                if value == mobase.ModState.ACTIVE:
                    if quoted_modname not in config_json_content:
                        substr = "knownMods:["
                        config_json_content = config_json_content.replace(
                            substr, substr + quoted_modname + ","
                        )
                        substr = "loadOrder:["
                        config_json_content = config_json_content.replace(
                            substr, substr + quoted_modname + ","
                        )
                        changed = True
                else:
                    old_content = config_json_content
                    config_json_content = config_json_content.replace(
                        quoted_modname + ",", ""
                    )
                    config_json_content = config_json_content.replace(
                        "," + quoted_modname, ""
                    )
                    changed = config_json_content != old_content

                if changed:
                    config_json_content = config_json_content.replace(",,", ",")
                    config_json_content = config_json_content.replace(
                        ",],modOptions", "],modOptions"
                    )
                    config_json_content = config_json_content.replace(
                        ",],developer", "],developer"
                    )
                    try:
                        with open(
                            SMM_Config_Json, "w", encoding="utf-8"
                        ) as config_json:
                            config_json.write(config_json_content)
                    except OSError:
                        return None
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
    def baseDlls(self) -> set[str]:
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
            if relpath and e.hasSuffix("dll") and relpath not in self.baseDlls:
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
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)
        super().initializeProfile(directory, settings)
