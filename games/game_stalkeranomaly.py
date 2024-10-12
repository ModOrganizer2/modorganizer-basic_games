# -*- encoding: utf-8 -*-

from pathlib import Path
from typing import List
from enum import IntEnum
import shutil

try:
    from PyQt6.QtCore import QDir, QFileInfo, Qt
    from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
except:
    from PyQt5.QtCore import Qt, QDir, QFileInfo
    from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

import mobase

from ..basic_features.basic_save_game_info import (
    BasicGameSaveGame,
    BasicGameSaveGameInfo,
)
from ..basic_game import BasicGame

from .stalkeranomaly import XRSave




def is_dir_empty(dir: Path):
    return not any(Path(dir).iterdir())

def move_file(source: Path, target: Path):
    if not target.parent.exists():
        target.parent.mkdir(parents=True)
    shutil.move(str(source.resolve()), str(target.resolve()))

def replace_file(source: Path, target: Path):
    shutil.copytree(str(source.resolve()), str(target.resolve()), dirs_exist_ok=True)
    shutil.rmtree(str(source.resolve()))

def copy_file(source: Path, target: Path):
    if not target.parent.exists():
        target.parent.mkdir(parents=True)

    if not target.exists():
        target.mkdir(parents=True)

    try:
        shutil.copytree(str(source.resolve()), str(target.resolve()), dirs_exist_ok=True)
    except:
        shutil.copy2(str(source.resolve()), str(target.resolve()))

class StalkerAnomalyModDataChecker(mobase.ModDataChecker):
    _valid_folders: List[str] = [
        "appdata",
        "bin",
        "db",
        "gamedata",
    ]

    def hasValidFolders(self, tree: mobase.IFileTree) -> bool:
        for e in tree:
            if e.isDir():
                if e.name().lower() in self._valid_folders:
                    return True

        return False

    def findLostData(self, tree: mobase.IFileTree) -> List[mobase.FileTreeEntry]:
        lost_db: List[mobase.FileTreeEntry] = []

        for e in tree:
            if e.isFile():
                if e.suffix().lower().startswith("db"):
                    lost_db.append(e)

        return lost_db

    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        if self.hasValidFolders(tree):
            return mobase.ModDataChecker.VALID

        if self.findLostData(tree):
            return mobase.ModDataChecker.FIXABLE

        return mobase.ModDataChecker.INVALID

    def fix(self, tree: mobase.IFileTree) -> mobase.IFileTree:
        lost_db = self.findLostData(tree)
        if lost_db:
            rfolder = tree.addDirectory("db").addDirectory("mods")
            for r in lost_db:
                rfolder.insert(r, mobase.IFileTree.REPLACE)

        return tree


class Content(IntEnum):
    INTERFACE = 0
    TEXTURE = 1
    MESH = 2
    SCRIPT = 3
    SOUND = 4
    MCM = 5
    CONFIG = 6


class StalkerAnomalyModDataContent(mobase.ModDataContent):
    content: List[int] = []

    def getAllContents(self) -> List[mobase.ModDataContent.Content]:
        return [
            mobase.ModDataContent.Content(
                Content.INTERFACE, "Interface", ":/MO/gui/content/interface"
            ),
            mobase.ModDataContent.Content(
                Content.TEXTURE, "Textures", ":/MO/gui/content/texture"
            ),
            mobase.ModDataContent.Content(
                Content.MESH, "Meshes", ":/MO/gui/content/mesh"
            ),
            mobase.ModDataContent.Content(
                Content.SCRIPT, "Scripts", ":/MO/gui/content/script"
            ),
            mobase.ModDataContent.Content(
                Content.SOUND, "Sounds", ":/MO/gui/content/sound"
            ),
            mobase.ModDataContent.Content(Content.MCM, "MCM", ":/MO/gui/content/menu"),
            mobase.ModDataContent.Content(
                Content.CONFIG, "Configs", ":/MO/gui/content/inifile"
            ),
        ]

    def walkContent(
        self, path: str, entry: mobase.FileTreeEntry
    ) -> mobase.IFileTree.WalkReturn:
        name = entry.name().lower()
        if entry.isFile():
            ext = entry.suffix().lower()
            if ext in ["dds", "thm"]:
                self.content.append(Content.TEXTURE)
                if path.startswith("gamedata/textures/ui"):
                    self.content.append(Content.INTERFACE)
            elif ext in ["omf", "ogf"]:
                self.content.append(Content.MESH)
            elif ext in ["script"]:
                self.content.append(Content.SCRIPT)
                if "_mcm" in name:
                    self.content.append(Content.MCM)
            elif ext in ["ogg"]:
                self.content.append(Content.SOUND)
            elif ext in ["ltx", "xml"]:
                self.content.append(Content.CONFIG)
                if path.startswith("gamedata/configs/ui"):
                    self.content.append(Content.INTERFACE)

        return mobase.IFileTree.WalkReturn.CONTINUE

    def getContentsFor(self, tree: mobase.IFileTree) -> List[int]:
        self.content = []
        tree.walk(self.walkContent, "/")
        return self.content


class StalkerAnomalySaveGame(BasicGameSaveGame):
    _filepath: Path

    xr_save: XRSave

    def __init__(self, filepath: Path):
        super().__init__(filepath)
        self._filepath = filepath
        self.xr_save = XRSave(self._filepath)

    def getName(self) -> str:
        xr_save = self.xr_save
        player = xr_save.player
        if player:
            name = player.character_name_str
            time = xr_save.time_fmt
            return f"{name}, {xr_save.save_fmt} [{time}]"
        return ""

    def allFiles(self) -> List[str]:
        filepath = str(self._filepath)
        paths = [filepath]
        scoc = filepath.replace(".scop", ".scoc")
        if Path(scoc).exists():
            paths.append(scoc)
        dds = filepath.replace(".scop", ".dds")
        if Path(dds).exists():
            paths.append(dds)
        return paths


class StalkerAnomalySaveGameInfoWidget(mobase.ISaveGameInfoWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        layout = QVBoxLayout()
        self._labelSave = self.newLabel(layout)
        self._labelName = self.newLabel(layout)
        self._labelFaction = self.newLabel(layout)
        self._labelHealth = self.newLabel(layout)
        self._labelMoney = self.newLabel(layout)
        self._labelRank = self.newLabel(layout)
        self._labelRep = self.newLabel(layout)
        self.setLayout(layout)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.black)
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        self.setWindowFlags(Qt.ToolTip | Qt.BypassGraphicsProxyWidget)  # type: ignore

    def newLabel(self, layout: QVBoxLayout) -> QLabel:
        label = QLabel()
        label.setAlignment(Qt.AlignLeft)
        palette = label.palette()
        palette.setColor(label.foregroundRole(), Qt.white)
        label.setPalette(palette)
        layout.addWidget(label)
        layout.addStretch()
        return label

    def setSave(self, save: mobase.ISaveGame):
        self.resize(240, 32)
        if not isinstance(save, StalkerAnomalySaveGame):
            return
        xr_save = save.xr_save
        player = xr_save.player
        if player:
            self._labelSave.setText(f"Save: {xr_save.save_fmt}")
            self._labelName.setText(f"Name: {player.character_name_str}")
            self._labelFaction.setText(f"Faction: {xr_save.getFaction()}")
            self._labelHealth.setText(f"Health: {player.health:.2f}%")
            self._labelMoney.setText(f"Money: {player.money} RU")
            self._labelRank.setText(f"Rank: {xr_save.getRank()} ({player.rank})")
            self._labelRep.setText(
                f"Reputation: {xr_save.getReputation()} ({player.reputation})"
            )


class StalkerAnomalySaveGameInfo(BasicGameSaveGameInfo):
    def getSaveGameWidget(self, parent=None):
        return StalkerAnomalySaveGameInfoWidget(parent)



class StalkerAnomalyLocalSavegames(mobase.LocalSavegames):
    def __init__(self, myGameSaveDir):
        super().__init__()
        self._savesDir = myGameSaveDir.absolutePath()

    def create_appdata_content(self, profile_save_dir):
        profile_dir = Path(profile_save_dir.absolutePath())
        profile_appdata = profile_dir.joinpath('saves/appdata')

        if not profile_appdata.exists():
            profile_appdata.mkdir()

        if not profile_appdata.joinpath('logs').exists():
            profile_appdata.joinpath('logs').mkdir()

        if not profile_appdata.joinpath('savedgames').exists():
            profile_appdata.joinpath('savedgames').mkdir()

        if not profile_appdata.joinpath('shaders_cache').exists():
            profile_appdata.joinpath('shaders_cache').mkdir()

        if not profile_appdata.joinpath('screenshots').exists():
            profile_appdata.joinpath('screenshots').mkdir()

        if not profile_appdata.joinpath('user.ltx').exists():
            (Path(  profile_appdata / "user.ltx"  )).write_text(" ")

    def mappings(self, profile_save_dir):
        root_game = Path(self._savesDir).parent


        profile_src = profile_save_dir.absolutePath()   + '/appdata'
        profile_dest = Path(self._savesDir)
        profile_dest = str(profile_dest.resolve())
        print(f'!{profile_src = }')
        print(f'!{profile_dest = }')

        # if not Path(profile_src).exists():
        #     Path(profile_src).mkdir()

        root_src= Path(self._savesDir).parent.joinpath("appdata")
        root_dest = Path(self._savesDir).parent.joinpath("mo__appdata")

        root_src.rename(root_dest)
        root_src.mkdir()

        return [
            mobase.Mapping(
                source=profile_src,
                destination=profile_dest,
                is_directory=True,
                create_target=True,
            )
            ]

    def prepareProfile(self, profile):
        return profile.localSavesEnabled()


class StalkerAnomalyGame(BasicGame, mobase.IPluginFileMapper):
    Name = "STALKER Anomaly"
    Author = "Qudix,YesMan"
    Version = "0.6.0"
    Description = "Adds support for STALKER Anomaly"

    GameName = "STALKER Anomaly"
    GameShortName = "stalkeranomaly"
    GameNexusName = "stalkeranomaly"
    GameNexusId = 3743
    GameBinary = "AnomalyLauncher.exe"
    GameDataPath = ""
    GameDocumentsDirectory = "%GAME_PATH%/appdata"

    GameSaveExtension = "scop"
    GameSavesDirectory = "%GAME_PATH%/appdata"

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)

    def init(self, organizer: mobase.IOrganizer):
        BasicGame.init(self, organizer)
        self._featureMap[mobase.ModDataChecker] = StalkerAnomalyModDataChecker()
        self._featureMap[mobase.ModDataContent] = StalkerAnomalyModDataContent()
        ## TODO: reimplement save game info
        # self._featureMap[mobase.SaveGameInfo] = StalkerAnomalySaveGameInfo()
        self._featureMap[mobase.LocalSavegames] = StalkerAnomalyLocalSavegames(
            self.savesDirectory()
        )
        self._register_event_handler()
        self.localsaves = False
        return True


    def does_moappdata_exist(self) -> bool:
        root_game = Path(self.GameSavesDirectory).parent
        mo_appdata = root_game.joinpath('mo__appdata')

        return mo_appdata.exists()


    def does_appdata_exist(self):
        root_game = Path(self.GameSavesDirectory).parent
        appdata = root_game.joinpath('appdata')

        return appdata.exists()


    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        self._featureMap[mobase.LocalSavegames] = StalkerAnomalyLocalSavegames(
            self.savesDirectory()
        )

        super().initializeProfile(directory, settings)


    def aboutToRun(self, _str: str) -> bool:
        gamedir = self.gameDirectory()
        if gamedir.exists():
            # For mappings
            if gamedir.joinpath("mo__appdata").exists():
                if gamedir.joinpath("mo__appdata").exists():
                    replace_file(gamedir.joinpath("mo__appdata"), gamedir.joinpath("appdata"))
            else:
                gamedir.mkdir("appdata")
            # The game will crash if this file exists in the
            # virtual tree rather than the game dir
            dbg_path = Path(self._gamePath, "gamedata/configs/cache_dbg.ltx")
            if not dbg_path.exists():
                dbg_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dbg_path, "w", encoding="utf-8") as file:  # noqa
                    pass
        return True

    def executables(self) -> List[mobase.ExecutableInfo]:
        info = [
            ["Anomaly Launcher", "AnomalyLauncher.exe"],
            ["Anomaly (DX11-AVX)", "bin/AnomalyDX11AVX.exe"],
            ["Anomaly (DX11)", "bin/AnomalyDX11.exe"],
            ["Anomaly (DX10-AVX)", "bin/AnomalyDX10AVX.exe"],
            ["Anomaly (DX10)", "bin/AnomalyDX10.exe"],
            ["Anomaly (DX9-AVX)", "bin/AnomalyDX9AVX.exe"],
            ["Anomaly (DX9)", "bin/AnomalyDX9.exe"],
            ["Anomaly (DX8-AVX)", "bin/AnomalyDX8AVX.exe"],
            ["Anomaly (DX8)", "bin/AnomalyDX8.exe"],
        ]
        gamedir = self.gameDirectory()
        return [
            mobase.ExecutableInfo(inf[0], QFileInfo(gamedir, inf[1])) for inf in info
        ]

    def listSaves(self, folder: QDir) -> List[mobase.ISaveGame]:
        save_games = super().listSaves(folder)
        path = Path(folder.absolutePath() + '/savedgames')
        ext = self._mappings.savegameExtension.get()
        save_games.extend(StalkerAnomalySaveGame(f) for f in path.glob(f"*.{ext}"))
        return save_games



    def create_appdata_content(self, profile):
        profile_dir = Path( profile.absolutePath() )
        print(f'{profile_dir = }')
        profile_appdata = profile_dir.joinpath('saves/appdata')

        # print(f'{profile_appdata.absolute() = }')
        if not profile_appdata.exists():
            # if not profile_dir.joinpath('saves').exists():
            profile_appdata.mkdir(parents=True)

        if not profile_appdata.joinpath('logs').exists():
            profile_appdata.joinpath('logs').mkdir()

        if not profile_appdata.joinpath('savedgames').exists():
            profile_appdata.joinpath('savedgames').mkdir()

        if not profile_appdata.joinpath('shaders_cache').exists():
            profile_appdata.joinpath('shaders_cache').mkdir()

        if not profile_appdata.joinpath('screenshots').exists():
            profile_appdata.joinpath('screenshots').mkdir()

        if not profile_appdata.joinpath('user.ltx').exists():
            (Path(  profile_appdata / "user.ltx"  )).write_text(" ")

    def copy_base_appdata_content(self, profile):
        profile_dir = Path( profile.absolutePath() )
        profile_appdata = profile_dir.joinpath('saves/appdata')
        root_appdata = Path(self.savesDirectory().absolutePath())
        print(f'{root_appdata.absolute() = }')
        print(f'{(profile_appdata.joinpath("logs").absolute())} = ')
        # copy_file(root_appdata.joinpath('logs').absolute(), profile_appdata.absolute())
        # shutil.copy2(root_appdata.joinpath('logs/xray_allinux.log').absolute(), profile_appdata.joinpath('logs').absolute())
        # shutil.copy2(root_appdata.joinpath('user.ltx').absolute(), profile_appdata.absolute())

        # print('root_appdata contents')
        # for f in root_appdata.joinpath('logs').iterdir():
        #     print(f)

        copy_file(root_appdata, profile_appdata)
        return True


    def mappings(self) -> List[mobase.Mapping]:
        appdata = self.gameDirectory().filePath("appdata")
        m = mobase.Mapping()
        m.createTarget = True
        m.isDirectory = True
        m.source = appdata
        m.destination = appdata
        return [m]


    def _register_event_handler(self):
        self._organizer.onUserInterfaceInitialized(lambda win: self._organizer_onUiInitalized_event_handler())
        self._organizer.onAboutToRun(self._game_aboutToRun_event_handler)
        self._organizer.onFinishedRun(self._game_finished_event_handler)
        self._organizer.onProfileCreated(self._organizer_onProfileCreated_event_handler)
        self._organizer.onProfileChanged(self._organizer_onProfileChanged_event_handler)

        if self._organizer.appVersion().displayString()[0:3].find('2.5') > 0:
            immediate_if_possible:bool = True
            # self._organizer.onNextRefresh(self._organizer_onNextRefresh_event_handler, immediate_if_possible)
        else:
            pass


    # version 2.5 or greater
    def _organizer_onNextRefresh_event_handler(self) -> bool:
        root_game = Path(self.GameSavesDirectory).parent
        appdata = root_game.joinpath('appdata')
        mo_appdata = root_game.joinpath('mo__appdata')

        # if not self.does_appdata_exist():
        #     if self.does_moappdata_exist():

        #         mo_appdata.rename(appdata)
        #         # self._organizer_onNextRefresh_event_handler(_organizer_onNextRefresh_event_handler)

        #     else:
        #         appdata.rename(appdata)

        # elif self.does_appdata_exist():
        #     if self.does_moappdata_exist() and ( len(appdata.glob('*')) <= 1):
        #         appdata.rename("test")


    def _organizer_onUiInitalized_event_handler(self) -> bool:
        self.UiInitialized = True


    def _organizer_onProfileCreated_event_handler(self, newProfile):
        print("_organizer_onProfileCreated_event_handler")

        root_game = Path( self.gameDirectory().absolutePath() )
        game_appdata = root_game.joinpath('appdata')
        mo_appdata = root_game.joinpath('mo__appdata')

        if newProfile.localSavesEnabled():
            self.localsaves = True
            self.create_appdata_content(newProfile)

        # if newProfile.localSavesEnabled() and not mo__appdata.exists():
            # if newProfile.
            # self.create_appdata_content(newProfile)
            # # if Default profile exists
            # default_pro = profile_dir.parent.joinpath('Default')
        # if mo_appdata.exists():
        #     if game_appdata.exists():
        #         # try:
        #         game_appdata.rmdir()
        #         # except():
        #     mo_appdata.rename(game_appdata)

    def _organizer_onProfileChanged_event_handler(self, oldProfile, newProfile ):
        print("_organizer_onProfileChanged_event_handler")

        root_game = Path( self.gameDirectory().absolutePath() )
        game_appdata = root_game.joinpath('appdata')
        mo_appdata = root_game.joinpath('mo__appdata')

        self.localsaves = newProfile.localSavesEnabled


        if newProfile.localSavesEnabled():
            print("new profile local saves enabled")
            # if newProfile.
            self.create_appdata_content(newProfile)

        return True

    def _game_aboutToRun_event_handler(self, _str: str) -> bool:
        print("_game_aboutToRun_event_handler")
        gamedir = self.gameDirectory()
        if gamedir.exists():
            # For mappings
            # gamedir.mkdir("appdata")
            # The game will crash if this file exists in the
            # virtual tree rather than the game dir

            # local saves
            root_game = Path( self.gameDirectory().absolutePath() )
            game_appdata = root_game.joinpath('appdata')
            mo_appdata = root_game.joinpath('mo__appdata')
            if root_game.joinpath("mo__appdata").exists():
                replace_file(root_game.joinpath("mo__appdata"), root_game.joinpath("appdata"))

            # if root_game.joinpath("")



            dbg_path = Path(self._gamePath, "gamedata/configs/cache_dbg.ltx")
            if not dbg_path.exists():
                dbg_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dbg_path, "w", encoding="utf-8"):
                    pass
        return True


    def _game_finished_event_handler(self, app_path: str, exit_code: int) -> None:
        print("_game_finished_event_handler")

        root_game = Path( self.gameDirectory().absolutePath() )
        appdata = root_game.joinpath('appdata')
        mo_appdata = root_game.joinpath('mo__appdata')
        if mo_appdata.exists():
            replace_file(mo_appdata, appdata)
