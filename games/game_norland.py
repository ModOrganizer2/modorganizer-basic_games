from PyQt6.QtCore import QDir

import mobase

from ..basic_game import BasicGame


class NorlandModDataChecker(mobase.ModDataChecker):
    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        entries = list(filetree)
        if entries and all(self._belongs(entry) for entry in entries):
            return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.INVALID

    @staticmethod
    def _belongs(entry: mobase.FileTreeEntry) -> bool:
        name = entry.name().casefold()
        if isinstance(entry, mobase.IFileTree):
            return name == "nlse" or entry.exists("mod.json", mobase.IFileTree.FILE)
        return name == "nlse.dll"


class NorlandGame(BasicGame):
    Name = "Norland Support Plugin"
    Author = "hkyss"
    Version = "0.3.1"

    GameName = "Norland"
    GameShortName = "norland"
    GameNexusName = "norland"
    GameNexusId = 10369
    GameSteamId = 1857090
    GameBinary = "Norland.exe"
    GameDataPath = "mods"
    GameDocumentsDirectory = "%USERPROFILE%/AppData/Local/Strategy"
    GameSavesDirectory = "%GAME_DOCUMENTS%/saves"
    GameSaveExtension = "norland"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(NorlandModDataChecker())
        return True

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        path = self.dataDirectory().absoluteFilePath("nlse.dll")
        loader = QDir.toNativeSeparators(path)
        setting = mobase.ExecutableForcedLoadSetting(self.binaryName(), loader)
        return [setting.withEnabled(True)]
