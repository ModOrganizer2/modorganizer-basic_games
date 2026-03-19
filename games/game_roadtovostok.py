import os
import shutil

import mobase
from PyQt6.QtCore import QDir, QFileInfo

from ..basic_game import BasicGame

class RoadToVostokModDataChecker(mobase.ModDataChecker):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self.organizer: mobase.IOrganizer = organizer

    def dataLooksValid(self, filetree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:

        if filetree.exists("mods", mobase.IFileTree.DIRECTORY) and not filetree.exists("mod.txt", mobase.IFileTree.FILE):
            return mobase.ModDataChecker.VALID
        for e in filetree:
            if e is not None and e.isFile() and e.suffix().casefold() == "pck":
                return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.FIXABLE

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        GameModsPath = self.organizer.managedGame().GameModsPath + "/"
        treefixed = 0

        for branch in filetree:
            mod_name = filetree.name()
            if mod_name == "":
                mod_name = branch.name()
            mod_path = os.path.join(self.organizer.modsPath(), mod_name)
            if filetree.createOrphanTree("OrphanTree") is None and os.path.exists(mod_path) and branch.suffix().casefold() == "zip":
                os.makedirs(os.path.join(mod_path, GameModsPath), exist_ok=True)
                shutil.move(os.path.join(mod_path, branch.name()), os.path.join(mod_path, GameModsPath, branch.name()))
                treefixed = 1

        if treefixed == 0:
            return None
        return filetree


class RoadToVostokGame(BasicGame):

    Name = "Road to Vostok Support Plugin"
    Author = "modworkshop" 
    Version = "1"
    GameName = "Road to Vostok"
    GameShortName = "road-to-vostok"
    GameSteamId = 1963610
    GameBinary = "Road_to_Vostok_Demo.exe"
    GameDataPath = "%GAME_PATH%"
    GameModsPath = "mods"
    GameDocumentsDirectory = "%USERPROFILE%/AppData/Local/Godot/app_userdata/Road to Vostok"
    GameSaveExtension = "tres"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = RoadToVostokModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        return True

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Road to Vostok (Use Injector)",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ).withArgument("--main-pack Injector.pck"),
            mobase.ExecutableInfo(
                "Road to Vostok (No Mods)",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
        ]

    def iniFiles(self):
        return ["settings.cfg"]

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        modsPath = self.dataDirectory().absolutePath()
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)
        super().initializeProfile(directory, settings)
