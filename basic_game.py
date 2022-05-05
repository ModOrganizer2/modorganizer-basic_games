# -*- encoding: utf-8 -*-

import shutil
import sys
from pathlib import Path
from typing import Callable, Dict, Generic, List, Optional, TypeVar, Union

from PyQt6.QtCore import QDir, QFileInfo, QStandardPaths
from PyQt6.QtGui import QIcon

import mobase

from .basic_features.basic_save_game_info import BasicGameSaveGame


def replace_variables(value: str, game: "BasicGame") -> str:
    """Replace special paths in the given value."""

    if value.find("%DOCUMENTS%") != -1:
        value = value.replace(
            "%DOCUMENTS%",
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.DocumentsLocation
            ),
        )
    if value.find("%USERPROFILE%") != -1:
        value = value.replace(
            "%USERPROFILE%",
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.HomeLocation
            ),
        )
    if value.find("%GAME_DOCUMENTS%") != -1:
        value = value.replace(
            "%GAME_DOCUMENTS%", game.documentsDirectory().absolutePath()
        )
    if value.find("%GAME_PATH%") != -1:
        value = value.replace("%GAME_PATH%", game.gameDirectory().absolutePath())

    return value


T = TypeVar("T")


class BasicGameMapping(Generic[T]):

    # The game:
    _game: "BasicGame"

    # Name of the attribute for exposure:
    _exposed_name: str

    # Name of the internal method:
    _internal_method_name: str

    # Required:
    _required: bool

    # Callable returning a default value (if not required):
    _default: Callable[["BasicGame"], T]

    # Function to apply to the value:
    _apply_fn: Optional[Callable[[Union[T, str]], T]]

    def __init__(
        self,
        game,
        exposed_name,
        internal_method,
        default: Optional[Callable[["BasicGame"], T]] = None,
        apply_fn: Optional[Callable[[Union[T, str]], T]] = None,
    ):

        self._game = game
        self._exposed_name = exposed_name
        self._internal_method_name = internal_method
        self._apply_fn = apply_fn

        if hasattr(game, self._exposed_name):
            value = getattr(game, self._exposed_name)

            if self._apply_fn is not None:
                try:
                    value = self._apply_fn(value)
                except:  # noqa
                    raise ValueError(
                        "Basic game plugin from {} has an invalid {} property.".format(
                            game._fromName, self._exposed_name
                        )
                    )
            self._default = lambda game: value  # type: ignore
        elif default is not None:
            self._default = default  # type: ignore
        elif getattr(game.__class__, self._internal_method_name) is getattr(
            BasicGame, self._internal_method_name
        ):
            raise ValueError(
                "Basic game plugin from {} is missing {} property.".format(
                    game._fromName, self._exposed_name
                )
            )

    def get(self) -> T:
        """Return the value of this mapping."""
        value = self._default(self._game)  # type: ignore

        if isinstance(value, str):
            return replace_variables(value, self._game)  # type: ignore
        elif isinstance(value, QDir):
            return QDir(replace_variables(value.path(), self._game))  # type: ignore

        # MO2 does not support Path anywhere so we always convert to str:
        elif isinstance(value, Path):
            return replace_variables(str(value), self._game)  # type: ignore

        return value


class BasicGameOptionsMapping(BasicGameMapping[List[T]]):

    """
    Represents a game mappings for which multiple options are possible. The game
    plugin is responsible to choose the right option depending on the context.
    """

    _index: int

    def __init__(
        self,
        game,
        exposed_name,
        internal_method,
        default: Optional[Callable[["BasicGame"], T]] = None,
        apply_fn: Optional[Callable[[Union[List[T], str]], List[T]]] = None,
    ):
        super().__init__(game, exposed_name, internal_method, lambda g: [], apply_fn)
        self._index = -1
        self._current_default = default

    def set_index(self, index: int):
        """
        Set the index of the option to use.

        Args:
            index: Index of the option to use.
        """
        self._index = index

    def set_value(self, value: T):
        """
        Set the index corresponding of the given value. If the value is not present,
        the index is set to -1.

        Args:
            value: The value to set the index to.
        """
        try:
            self._index = self.get().index(value)
        except ValueError:
            self._index = -1

    def has_value(self) -> bool:
        """
        Check if a value was set for this options mapping.

        Returns:
            True if a value was set, False otherwise.
        """
        return self._index != -1

    def current(self) -> T:
        values = self._default(self._game)  # type: ignore

        if not values:
            return self._current_default(self._game)  # type: ignore

        if self._index == -1:
            value = values[0]
        else:
            value = values[self._index]

        if isinstance(value, str):
            return replace_variables(value, self._game)  # type: ignore
        elif isinstance(value, QDir):
            return QDir(replace_variables(value.path(), self._game))  # type: ignore

        return value


class BasicGameMappings:

    name: BasicGameMapping[str]
    author: BasicGameMapping[str]
    version: BasicGameMapping[mobase.VersionInfo]
    description: BasicGameMapping[str]
    gameName: BasicGameMapping[str]
    gameShortName: BasicGameMapping[str]
    gameNexusName: BasicGameMapping[str]
    validShortNames: BasicGameMapping[List[str]]
    nexusGameId: BasicGameMapping[int]
    binaryName: BasicGameMapping[str]
    launcherName: BasicGameMapping[str]
    dataDirectory: BasicGameMapping[str]
    documentsDirectory: BasicGameMapping[QDir]
    savesDirectory: BasicGameMapping[QDir]
    savegameExtension: BasicGameMapping[str]
    steamAPPId: BasicGameOptionsMapping[str]
    gogAPPId: BasicGameOptionsMapping[str]
    originManifestIds: BasicGameOptionsMapping[str]
    originWatcherExecutables: BasicGameMapping[List[str]]
    epicAPPId: BasicGameOptionsMapping[str]
    eaDesktopContentId: BasicGameOptionsMapping[str]
    supportURL: BasicGameMapping[str]

    @staticmethod
    def _default_documents_directory(game):

        folders = [
            "{}/My Games/{}".format(
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.DocumentsLocation
                ),
                game.gameName(),
            ),
            "{}/{}".format(
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.DocumentsLocation
                ),
                game.gameName(),
            ),
        ]
        for folder in folders:
            qdir = QDir(folder)
            if qdir.exists():
                return qdir

        return QDir()

    # Game mappings:
    def __init__(self, game: "BasicGame"):
        self._game = game

        self.name = BasicGameMapping(game, "Name", "name")
        self.author = BasicGameMapping(game, "Author", "author")
        self.version = BasicGameMapping(
            game,
            "Version",
            "version",
            apply_fn=lambda s: mobase.VersionInfo(s) if isinstance(s, str) else s,
        )
        self.description = BasicGameMapping(
            game,
            "Description",
            "description",
            lambda g: "Adds basic support for game {}.".format(g.gameName()),
        )
        self.gameName = BasicGameMapping(game, "GameName", "gameName")
        self.gameShortName = BasicGameMapping(game, "GameShortName", "gameShortName")
        self.gameNexusName = BasicGameMapping(
            game,
            "GameNexusName",
            "gameNexusName",
            default=lambda g: g.gameShortName(),
        )
        self.validShortNames = BasicGameMapping(
            game,
            "GameValidShortNames",
            "validShortNames",
            default=lambda g: [],
            apply_fn=lambda value: [c.strip() for c in value.split(",")]  # type: ignore
            if isinstance(value, str)
            else value,
        )
        self.nexusGameId = BasicGameMapping(
            game, "GameNexusId", "nexusGameID", default=lambda g: 0, apply_fn=int
        )
        self.binaryName = BasicGameMapping(game, "GameBinary", "binaryName")
        self.launcherName = BasicGameMapping(
            game,
            "GameLauncher",
            "getLauncherName",
            default=lambda g: "",
        )
        self.dataDirectory = BasicGameMapping(game, "GameDataPath", "dataDirectory")
        self.documentsDirectory = BasicGameMapping(
            game,
            "GameDocumentsDirectory",
            "documentsDirectory",
            apply_fn=lambda s: QDir(s) if isinstance(s, str) else s,
            default=BasicGameMappings._default_documents_directory,
        )
        self.savesDirectory = BasicGameMapping(
            game,
            "GameSavesDirectory",
            "savesDirectory",
            apply_fn=lambda s: QDir(s) if isinstance(s, str) else s,
            default=lambda g: g.documentsDirectory(),
        )
        self.savegameExtension = BasicGameMapping(
            game, "GameSaveExtension", "savegameExtension", default=lambda g: "save"
        )

        # Convert Union[int, str, List[Union[int, str]]] to List[str].
        def ids_apply(v) -> List[str]:
            if isinstance(v, (int, str)):
                v = [v]
            return [str(x) for x in v]

        self.steamAPPId = BasicGameOptionsMapping(
            game, "GameSteamId", "steamAPPId", default=lambda g: "", apply_fn=ids_apply
        )
        self.gogAPPId = BasicGameOptionsMapping(
            game, "GameGogId", "gogAPPId", default=lambda g: "", apply_fn=ids_apply
        )
        self.originManifestIds = BasicGameOptionsMapping(
            game,
            "GameOriginManifestIds",
            "originManifestIds",
            default=lambda g: "",
            apply_fn=ids_apply,
        )
        self.originWatcherExecutables = BasicGameMapping(
            game,
            "GameOriginWatcherExecutables",
            "originWatcherExecutables",
            apply_fn=lambda s: [s] if isinstance(s, str) else s,
            default=lambda g: [],
        )
        self.epicAPPId = BasicGameOptionsMapping(
            game, "GameEpicId", "epicAPPId", default=lambda g: "", apply_fn=ids_apply
        )
        self.eaDesktopContentId = BasicGameOptionsMapping(
            game,
            "GameEaDesktopId",
            "eaDesktopContentId",
            default=lambda g: "",
            apply_fn=ids_apply,
        )
        self.supportURL = BasicGameMapping(
            game, "GameSupportURL", "supportURL", default=lambda g: ""
        )


class BasicGame(mobase.IPluginGame):

    """This class implements some methods from mobase.IPluginGame
    to make it easier to create game plugins without having to implement
    all the methods of mobase.IPluginGame."""

    # List of steam, GOG, origin and Epic games:
    steam_games: Dict[str, Path]
    gog_games: Dict[str, Path]
    origin_games: Dict[str, Path]
    epic_games: Dict[str, Path]
    eadesktop_games: Dict[str, Path]

    @staticmethod
    def setup():
        from .eadesktop_utils import find_games as find_eadesktop_games
        from .epic_utils import find_games as find_epic_games
        from .gog_utils import find_games as find_gog_games
        from .origin_utils import find_games as find_origin_games
        from .steam_utils import find_games as find_steam_games

        BasicGame.steam_games = find_steam_games()
        BasicGame.gog_games = find_gog_games()
        BasicGame.origin_games = find_origin_games()
        BasicGame.epic_games = find_epic_games()
        BasicGame.eadesktop_games = find_eadesktop_games()

    # File containing the plugin:
    _fromName: str

    # Organizer obtained in init:
    _organizer: mobase.IOrganizer

    # Path to the game, as set by MO2:
    _gamePath: str

    # The feature map:
    _featureMap: Dict

    def __init__(self):
        super(BasicGame, self).__init__()

        if not hasattr(self, "_fromName"):
            self._fromName = self.__class__.__name__

        self._gamePath = ""
        self._featureMap = {}

        self._mappings: BasicGameMappings = BasicGameMappings(self)

    # Specific to BasicGame:
    def is_steam(self) -> bool:
        return self._mappings.steamAPPId.has_value()

    def is_gog(self) -> bool:
        return self._mappings.gogAPPId.has_value()

    def is_origin(self) -> bool:
        return self._mappings.originManifestIds.has_value()

    def is_epic(self) -> bool:
        return self._mappings.epicAPPId.has_value()

    def is_eadesktop(self) -> bool:
        return self._mappings.eaDesktopContentId.has_value()

    # IPlugin interface:

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self._organizer = organizer
        if self._mappings.originWatcherExecutables.get():
            from .origin_utils import OriginWatcher

            self.origin_watcher = OriginWatcher(
                self._mappings.originWatcherExecutables.get()
            )
            if not self._organizer.onAboutToRun(
                lambda appName: self.origin_watcher.spawn_origin_watcher()
            ):
                print("Failed to register onAboutToRun callback!", file=sys.stderr)
                return False
            if not self._organizer.onFinishedRun(
                lambda appName, result: self.origin_watcher.stop_origin_watcher()
            ):
                print("Failed to register onFinishedRun callback!", file=sys.stderr)
                return False
        return True

    def name(self) -> str:
        return self._mappings.name.get()

    def author(self) -> str:
        return self._mappings.author.get()

    def description(self) -> str:
        return self._mappings.description.get()

    def version(self) -> mobase.VersionInfo:
        return self._mappings.version.get()

    def isActive(self) -> bool:
        if not self._organizer.managedGame():
            return False

        # Note: self is self._organizer.managedGame() does not work:
        return self.name() == self._organizer.managedGame().name()

    def settings(self) -> List[mobase.PluginSetting]:
        return []

    # IPluginGame interface:

    def detectGame(self):
        for steam_id in self._mappings.steamAPPId.get():
            if steam_id in BasicGame.steam_games:
                self.setGamePath(BasicGame.steam_games[steam_id])
                return

        for gog_id in self._mappings.gogAPPId.get():
            if gog_id in BasicGame.gog_games:
                self.setGamePath(BasicGame.gog_games[gog_id])
                return

        for origin_manifest_id in self._mappings.originManifestIds.get():
            if origin_manifest_id in BasicGame.origin_games:
                self.setGamePath(BasicGame.origin_games[origin_manifest_id])
                return

        for epic_id in self._mappings.epicAPPId.get():
            if epic_id in BasicGame.epic_games:
                self.setGamePath(BasicGame.epic_games[epic_id])
                return

        for eadesktop_content_id in self._mappings.eaDesktopContentId.get():
            if eadesktop_content_id in BasicGame.eadesktop_games:
                self.setGamePath(BasicGame.eadesktop_games[eadesktop_content_id])
                return

    def gameName(self) -> str:
        return self._mappings.gameName.get()

    def gameShortName(self) -> str:
        return self._mappings.gameShortName.get()

    def gameIcon(self) -> QIcon:
        return mobase.getIconForExecutable(
            self.gameDirectory().absoluteFilePath(self.binaryName())
        )

    def validShortNames(self) -> List[str]:
        return self._mappings.validShortNames.get()

    def gameNexusName(self) -> str:
        return self._mappings.gameNexusName.get()

    def nexusModOrganizerID(self) -> int:
        return 0

    def nexusGameID(self) -> int:
        return self._mappings.nexusGameId.get()

    def steamAPPId(self) -> str:
        return self._mappings.steamAPPId.current()

    def gogAPPId(self) -> str:
        return self._mappings.gogAPPId.current()

    def epicAPPId(self) -> str:
        return self._mappings.epicAPPId.current()

    def eaDesktopContentId(self) -> str:
        return self._mappings.eaDesktopContentId.current()

    def binaryName(self) -> str:
        return self._mappings.binaryName.get()

    def getLauncherName(self) -> str:
        return self._mappings.launcherName.get()

    def getSupportURL(self) -> str:
        return self._mappings.supportURL.get()

    def executables(self) -> List[mobase.ExecutableInfo]:
        execs = []
        if self.getLauncherName():
            execs.append(
                mobase.ExecutableInfo(
                    self.gameName(),
                    QFileInfo(
                        self.gameDirectory().absoluteFilePath(self.getLauncherName())
                    ),
                )
            )
        execs.append(
            mobase.ExecutableInfo(
                self.gameName(),
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            )
        )
        return execs

    def executableForcedLoads(self) -> List[mobase.ExecutableForcedLoadSetting]:
        return []

    def listSaves(self, folder: QDir) -> List[mobase.ISaveGame]:
        ext = self._mappings.savegameExtension.get()
        return [
            BasicGameSaveGame(path)
            for path in Path(folder.absolutePath()).glob(f"**/*.{ext}")
        ]

    def initializeProfile(self, path: QDir, settings: mobase.ProfileSetting):
        if settings & mobase.ProfileSetting.CONFIGURATION:
            for iniFile in self.iniFiles():
                try:
                    shutil.copyfile(
                        self.documentsDirectory().absoluteFilePath(iniFile),
                        path.absoluteFilePath(QFileInfo(iniFile).fileName()),
                    )
                except FileNotFoundError:
                    Path(path.absoluteFilePath(QFileInfo(iniFile).fileName())).touch()

    def primarySources(self):
        return []

    def primaryPlugins(self):
        return []

    def gameVariants(self):
        return []

    def setGameVariant(self, variantStr):
        pass

    def gameVersion(self) -> str:
        return mobase.getFileVersion(
            self.gameDirectory().absoluteFilePath(self.binaryName())
        )

    def iniFiles(self):
        return []

    def DLCPlugins(self):
        return []

    def CCPlugins(self):
        return []

    def loadOrderMechanism(self):
        return mobase.LoadOrderMechanism.PluginsTxt

    def sortMechanism(self):
        return mobase.SortMechanism.NONE

    def looksValid(self, aQDir: QDir):
        return aQDir.exists(self.binaryName())

    def isInstalled(self) -> bool:
        return bool(self._gamePath)

    def gameDirectory(self) -> QDir:
        """
        @return directory (QDir) to the game installation.
        """
        return QDir(self._gamePath)

    def dataDirectory(self) -> QDir:
        return QDir(
            self.gameDirectory().absoluteFilePath(self._mappings.dataDirectory.get())
        )

    def setGamePath(self, path: Union[Path, str]):
        self._gamePath = str(path)

        path = Path(path)

        # Check if we have a matching steam, GOG, Origin or EA Desktop id and set the
        # index accordingly:
        for steamid, steampath in BasicGame.steam_games.items():
            if steampath == path:
                self._mappings.steamAPPId.set_value(steamid)
        for gogid, gogpath in BasicGame.gog_games.items():
            if gogpath == path:
                self._mappings.steamAPPId.set_value(gogid)
        for originid, originpath in BasicGame.origin_games.items():
            if originpath == path:
                self._mappings.originManifestIds.set_value(originid)
        for epicid, epicpath in BasicGame.epic_games.items():
            if epicpath == path:
                self._mappings.epicAPPId.set_value(epicid)
        for eadesktopid, eadesktoppath in BasicGame.eadesktop_games.items():
            if eadesktoppath == path:
                self._mappings.eaDesktopContentId.set_value(eadesktopid)

    def documentsDirectory(self) -> QDir:
        return self._mappings.documentsDirectory.get()

    def savesDirectory(self) -> QDir:
        return self._mappings.savesDirectory.get()

    def _featureList(self):
        return self._featureMap
