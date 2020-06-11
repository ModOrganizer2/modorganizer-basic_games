# -*- encoding: utf-8 -*-

from typing import List, Union, Optional, TypeVar, Callable, Generic, Dict


from PyQt5.QtCore import QDir, QFileInfo, QStandardPaths
from PyQt5.QtGui import QIcon

import mobase


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
        exposed_name,
        internal_method,
        default: Optional[Callable[["BasicGame"], T]] = None,
        apply_fn: Optional[Callable[[Union[T, str]], T]] = None,
    ):
        self._exposed_name = exposed_name
        self._internal_method_name = internal_method
        self._default = default
        self._apply_fn = apply_fn

    def init(self, game: "BasicGame"):
        BasicGame.__class__

        self._game = game

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
        return self._default(self._game)  # type: ignore


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
    _featureMap: Dict = {}

    # Game mappings:
    _name: BasicGameMapping[str] = BasicGameMapping("Name", "name")
    _author: BasicGameMapping[str] = BasicGameMapping("Author", "author")
    _version: BasicGameMapping[mobase.VersionInfo] = BasicGameMapping(
        "Version",
        "version",
        apply_fn=lambda s: mobase.VersionInfo(s) if isinstance(s, str) else s,
    )
    _description: BasicGameMapping[str] = BasicGameMapping(
        "Description",
        "description",
        lambda g: "Adds basic support for game {}.".format(g.gameName()),
    )
    _gameName: BasicGameMapping[str] = BasicGameMapping("GameName", "gameName")
    _gameShortName: BasicGameMapping[str] = BasicGameMapping(
        "GameShortName", "gameShortName"
    )
    _gameNexusName: BasicGameMapping[str] = BasicGameMapping(
        "GameNexusName", "gameNexusName", default=lambda g: g.gameShortName(),
    )
    _validShortNames: BasicGameMapping[List[str]] = BasicGameMapping(
        "GameValidShortNames",
        "validShortNames",
        default=lambda g: [],
        apply_fn=lambda value: [c.strip() for c in value.split(",")]
        if isinstance(value, str)
        else value,
    )
    _nexusGameId: BasicGameMapping[int] = BasicGameMapping(
        "GameNexusId", "nexusGameID", default=lambda g: 0, apply_fn=int
    )
    _binaryName: BasicGameMapping[str] = BasicGameMapping("GameBinary", "binaryName")
    _launcherName: BasicGameMapping[str] = BasicGameMapping(
        "GameLauncher", "getLauncherName", default=lambda g: "",
    )
    _dataDirectory: BasicGameMapping[str] = BasicGameMapping(
        "GameDataPath", "dataDirectory"
    )
    _savegameExtension: BasicGameMapping[str] = BasicGameMapping(
        "GameSaveExtension", "savegameExtension", default=lambda g: "save"
    )
    _steamAPPId: BasicGameMapping[str] = BasicGameMapping(
        "GameSteamId", "steamAPPId", default=lambda g: "", apply_fn=str
    )

    def __init__(self):
        super(BasicGame, self).__init__()

        #         if not hasattr(self, "_fromName"):
        self._fromName = self.__class__.__name__

        # We init the member and check that everything is provided:
        for name in dir(self):
            attr = getattr(self, name)
            if isinstance(attr, BasicGameMapping):
                attr.init(self)

    """
    Here IPlugin interface stuff.
    """

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self._organizer = organizer
        return True

    def name(self) -> str:
        return self._name.get()

    def author(self) -> str:
        return self._author.get()

    def description(self) -> str:
        return self._description.get()

    def version(self) -> mobase.VersionInfo:
        return self._version.get()

    def isActive(self) -> bool:
        return True

    def settings(self) -> List[mobase.PluginSetting]:
        return []

    def gameName(self) -> str:
        return self._gameName.get()

    def gameShortName(self) -> str:
        return self._gameShortName.get()

    def gameIcon(self) -> QIcon:
        return mobase.getIconForExecutable(
            self.gameDirectory().absoluteFilePath(self.binaryName())
        )

    def validShortNames(self) -> List[str]:
        return self._validShortNames.get()

    def gameNexusName(self) -> str:
        return self._gameNexusName.get()

    def nexusModOrganizerID(self) -> int:
        return 0

    def nexusGameID(self) -> int:
        return self._nexusGameId.get()

    def steamAPPId(self) -> str:
        return self._steamAPPId.get()

    def binaryName(self) -> str:
        return self._binaryName.get()

    def getLauncherName(self) -> str:
        return self._launcherName.get()

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

    def savegameExtension(self) -> str:
        return self._savegameExtension.get()

    def savegameSEExtension(self) -> str:
        return ""

    def initializeProfile(self, path: QDir, settings: int):
        pass

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
        return QDir(self.gameDirectory().absoluteFilePath(self._dataDirectory.get()))

    def setGamePath(self, pathStr: str):
        self._gamePath = pathStr

    def documentsDirectory(self) -> QDir:
        folders = [
            "{}/My Games/{}".format(
                QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation),
                self.gameName(),
            ),
            "{}/{}".format(
                QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation),
                self.gameName(),
            ),
        ]
        for folder in folders:
            qdir = QDir(folder)
            if qdir.exists():
                return qdir

        return QDir()

    def savesDirectory(self) -> QDir:
        return self.documentsDirectory()

    def _featureList(self):
        return self._featureMap
