
from PyQt6.QtCore import QDir
import mobase

from pathlib import Path
from ..basic_features.basic_save_game_info import BasicGameSaveGame
from ..basic_features.basic_local_savegames import BasicLocalSavegames
from ..steam_utils import find_steam_path
from ..basic_game import BasicGame

class FantasyLifeIModDataChecker(mobase.ModDataChecker):
    def __init__(self: mobase.ModDataChecker) -> None:
        super().__init__()

    def dataLooksValid(self: mobase.ModDataChecker, filetree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        if filetree.exists("Game", mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.INVALID
        
        if filetree.exists("Mods", mobase.IFileTree.DIRECTORY) or filetree.exists("Paks", mobase.IFileTree.DIRECTORY):
            return mobase.ModDataChecker.VALID
        
        return mobase.ModDataChecker.INVALID


class FantasyLifeI(BasicGame, 
                   mobase.IPluginFileMapper, 
                   mobase.IPluginInstallerSimple
                  ):
    
    Name = "Fantasy Life I Support Plugin"
    Author = "AmeliaCute"
    Version = "0.2.1"

    GameName = "FANTASY LIFE i"
    GameShortName = "fantasylifei"
    GameNexusName = "fantasylifeithegirlwhostealstime"
    GameValidShortNames = ["fli"]
    
    GameDataPath = "Game/Content/"
    GameBinary = "Game/Binaries/Win64/NFL1-Win64-Shipping.exe"
    GameSteamId = 2993780
    
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Fantasy-Life-I:-The-Girl-Who-Steals-Time"
    )

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)
        mobase.IPluginInstallerSimple.__init__(self)

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(FantasyLifeIModDataChecker())
        self._register_feature(BasicLocalSavegames(self.savesDirectory()))
        return True
    
    def executables(self):
        return [
            mobase.ExecutableInfo(
               "Fantasy Life i", self.GameBinary
            ),
        ]

    ## SAVE

    # credit to game.darkestdungeon.py
    @staticmethod
    def getCloudSaveDirectory() -> str | None:
        steamPath = find_steam_path()
        if steamPath is None:
            return None
        
        userData = steamPath.joinpath("userdata")
        for child in userData.iterdir():
            name = child.name
            try:
                int(name)
            except ValueError:
                continue

            cloudSaves = child.joinpath("2993780/remote")
            if cloudSaves.exists() and cloudSaves.is_dir():
                return str(cloudSaves)
        return None

    def savesDirectory(self) -> QDir:
        return QDir(self.getCloudSaveDirectory())

    def listSaves(self, folder: QDir) -> list[mobase.ISaveGame]:
        saves: list[Path] = []
        for path in Path(folder.absolutePath()).glob("*.bin"):
            saves.append(path)

        ##TODO: need a proper implementation
        return [BasicGameSaveGame(path) for path in saves]

    ## MAPPING

    def exeDirectory(self) -> QDir: return QDir(QDir(self.gameDirectory()).filePath("Game/Binaries/Win64"))

    def mappings(self) -> list[mobase.Mapping]:
        return [
            mobase.Mapping("*.dll", self.exeDirectory().absolutePath(), False, True),
        ]

    ## INSTALLER

    _PAK_EXTENSIONS = ('.pak', '.ucas', '.utoc')

    def priority(self) -> int:
        return 150

    def isArchiveSupported(self, tree: mobase.IFileTree) -> bool:
        for entry in tree:
            if entry.name().lower().endswith(self._PAK_EXTENSIONS): return True
        
        if tree.exists("Mod.json", mobase.IFileTree.FILE): return True
        return False

    def install(self, name: mobase.GuessedString, tree: mobase.IFileTree, version: str, nexus_id: int) -> mobase.InstallResult:

        for entry in list(tree):
            if entry.name().lower().endswith(self._PAK_EXTENSIONS):
                paks_dir = QDir(".").filePath("Paks")
                target_dir = QDir(paks_dir).filePath("~mods/")
                QDir().mkpath(target_dir)
                tree.move(entry, target_dir)
        
        if tree.exists("Mod.json", mobase.IFileTree.FILE):
            mods_dir = QDir(".").filePath("Mods")
            target_dir = QDir(mods_dir).filePath(f"{name.__str__()}/")
            QDir().mkpath(target_dir)

            for entry in list(tree): tree.move(entry, target_dir)
        
        return mobase.InstallResult.SUCCESS