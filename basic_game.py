# -*- encoding: utf-8 -*-

import shutil

from typing import List, Union, Optional, TypeVar, Callable, Generic, Dict


from PyQt5.QtCore import QDir, QFileInfo, QStandardPaths
from PyQt5.QtGui import QIcon

import mobase


def replace_variables(value: str, game: "BasicGame") -> str:
    """ Replace special paths in the given value. """

    if value.find("%DOCUMENTS%") != -1:
        value = value.replace(
            "%DOCUMENTS%",
            QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation),
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
    _default: Optional[Callable[["BasicGame"], T]]

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
        self._default = default
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
        elif self._default is not None:
            # Not required, ok!
            pass
        elif getattr(game.__class__, self._internal_method_name) is getattr(
            BasicGame, self._internal_method_name
        ):
            raise ValueError(
                "Basic game plugin from {} is missing {} property.".format(
                    game._fromName, self._exposed_name
                )
            )

    def get(self) -> T:
        """ Return the value of this mapping. """
        value = self._default(self._game)  # type: ignore

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
    steamAPPId: BasicGameMapping[str]

    @staticmethod
    def _default_documents_directory(game):

        folders = [
            "{}/My Games/{}".format(
                QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation),
                game.gameName(),
            ),
            "{}/{}".format(
                QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation),
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
            game, "GameNexusName", "gameNexusName", default=lambda g: g.gameShortName(),
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
            game, "GameLauncher", "getLauncherName", default=lambda g: "",
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
        self.steamAPPId = BasicGameMapping(
            game, "GameSteamId", "steamAPPId", default=lambda g: "", apply_fn=str
        )


class BasicGame(mobase.IPluginGame):

    """ This class implements some methods from mobase.IPluginGame
    to make it easier to create game plugins without having to implement
    all the methods of mobase.IPluginGame. """

    # List of steam games:
    steam_games: Dict[str, str]

    @staticmethod
    def setup():
        from .steam_utils import find_games

        BasicGame.steam_games = find_games()

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

        self.mappings: BasicGameMappings = BasicGameMappings(self)

    """
    Here IPlugin interface stuff.
    """

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self._organizer = organizer
        return True

    def name(self) -> str:
        return self.mappings.name.get()

    def author(self) -> str:
        return self.mappings.author.get()

    def description(self) -> str:
        return self.mappings.description.get()

    def version(self) -> mobase.VersionInfo:
        return self.mappings.version.get()

    def isActive(self) -> bool:
        return True

    def settings(self) -> List[mobase.PluginSetting]:
        return []

    def gameName(self) -> str:
        return self.mappings.gameName.get()

    def gameShortName(self) -> str:
        return self.mappings.gameShortName.get()

    def gameIcon(self) -> QIcon:
        return mobase.getIconForExecutable(
            self.gameDirectory().absoluteFilePath(self.binaryName())
        )

    def validShortNames(self) -> List[str]:
        return self.mappings.validShortNames.get()

    def gameNexusName(self) -> str:
        return self.mappings.gameNexusName.get()

    def nexusModOrganizerID(self) -> int:
        return 0

    def nexusGameID(self) -> int:
        return self.mappings.nexusGameId.get()

    def steamAPPId(self) -> str:
        return self.mappings.steamAPPId.get()

    def binaryName(self) -> str:
        return self.mappings.binaryName.get()

    def getLauncherName(self) -> str:
        return self.mappings.launcherName.get()

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

    def savegameExtension(self) -> str:
        return self.mappings.savegameExtension.get()

    def savegameSEExtension(self) -> str:
        return ""

    def initializeProfile(self, path: QDir, settings: int):
        if settings & mobase.ProfileSetting.CONFIGURATION:
            for iniFile in self.iniFiles():
                shutil.copyfile(
                    self.documentsDirectory().absoluteFilePath(iniFile),
                    path.absoluteFilePath(iniFile),
                )

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
        if self.steamAPPId() in BasicGame.steam_games:
            self.setGamePath(BasicGame.steam_games[self.steamAPPId()])
            return True

        return False

    def gameDirectory(self) -> QDir:
        """
        @return directory (QDir) to the game installation.
        """
        return QDir(self._gamePath)

    def dataDirectory(self) -> QDir:
        return QDir(
            self.gameDirectory().absoluteFilePath(self.mappings.dataDirectory.get())
        )

    def setGamePath(self, pathStr: str):
        self._gamePath = pathStr

    def documentsDirectory(self) -> QDir:
        return self.mappings.documentsDirectory.get()

    def savesDirectory(self) -> QDir:
        return self.mappings.savesDirectory.get()

    def _featureList(self):
        return self._featureMap
