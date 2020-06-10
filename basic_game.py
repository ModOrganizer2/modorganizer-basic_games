# -*- encoding: utf-8 -*-

import sys
import typing

from PyQt5.QtCore import QDir, QFileInfo, QStandardPaths

import mobase


class BasicGameMapping:

    # Name of the attribute for exposure:
    exposed_name: str

    # Name of the internal method:
    internal_method_name: str

    # Name of the internal attribute:
    internal_attribute_name: str

    # Required:
    required: bool

    # Default value (if not required):
    default: typing.Any

    # Function to apply to the value:
    apply_fn: typing.Callable

    def __init__(
        self,
        exposed_name,
        internal_method,
        internal_attribute=None,
        required: bool = True,
        default=None,
        apply_fn: typing.Callable = lambda x: x,
    ):
        self.exposed_name = exposed_name
        self.internal_method_name = internal_method
        if internal_attribute is None:
            self.internal_attribute_name = "_" + internal_method
        else:
            self.internal_attribute_name = internal_attribute
        self.required = required
        self.default = default
        self.apply_fn = apply_fn  # type: ignore


class BasicGame(mobase.IPluginGame):

    """ This class implements some methods from mobase.IPluginGame
    to make it easier to create game plugins without having to implement
    all the methods of mobase.IPluginGame. """

    # List of fields that can be provided by child class:
    Name: str
    Author: str
    Version: str
    Description: str

    GameName: str
    GameShortName: str
    GameBinary: str
    GameDataPath: str
    GameSaveExtension: str

    # File containing the plugin:
    _fromName: str

    # Organizer obtained in init:
    _organizer: mobase.IOrganizer

    # Path to the game, as set by MO2:
    _gamePath: str

    # The feature map:
    _featureMap: typing.Dict = {}

    # List of attributes - These should be the same as function with a
    # _ prefix:
    _name: str
    _author: str
    _version: mobase.VersionInfo
    _description: typing.Optional[str]
    _gameName: str
    _gameShortName: str
    _binaryName: str
    _dataDirectory: str
    _savegameExtension: str

    # Match the name of the public attribute (from child class), to the
    # name of the protected attribute and the corresponding function:
    NAME_MAPPING = [
        BasicGameMapping("Name", "name"),
        BasicGameMapping("Author", "author"),
        BasicGameMapping(
            "Version",
            "version",
            apply_fn=lambda s: mobase.VersionInfo(s) if isinstance(s, str) else s,
        ),
        BasicGameMapping("Description", "description", required=False),
        BasicGameMapping("GameName", "gameName"),
        BasicGameMapping("GameShortName", "gameShortName"),
        BasicGameMapping(
            "GameNexusName", "gameNexusName", required=False, default=None
        ),
        BasicGameMapping(
            "GameNexusId", "nexusGameID", required=False, default=0, apply_fn=int
        ),
        BasicGameMapping("GameBinary", "binaryName"),
        BasicGameMapping(
            "GameLauncher",
            "getLauncherName",
            "_launcherName",
            required=False,
            default="",
        ),
        BasicGameMapping("GameDataPath", "dataDirectory"),
        BasicGameMapping("GameSaveExtension", "savegameExtension"),
        BasicGameMapping(
            "GameSteamId", "steamAPPId", required=False, default="", apply_fn=str
        ),
    ]

    def __init__(self):
        super(BasicGame, self).__init__()

        #         if not hasattr(self, "_fromName"):
        self._fromName = self.__class__.__name__

        # We init the member and check that everything is provided:
        for basic_mapping in self.NAME_MAPPING:
            if hasattr(self, basic_mapping.exposed_name):
                try:
                    value = basic_mapping.apply_fn(
                        getattr(self, basic_mapping.exposed_name)
                    )
                except:  # noqa
                    print(
                        "Basic game plugin from {} has an invalid {} property.".format(
                            self._fromName, basic_mapping.exposed_name
                        ),
                        file=sys.stderr,
                    )
                    continue
                setattr(self, basic_mapping.internal_attribute_name, value)
            elif not basic_mapping.required:
                setattr(
                    self, basic_mapping.internal_attribute_name, basic_mapping.default
                )
            elif getattr(self, basic_mapping.internal_method_name) is getattr(
                BasicGame, basic_mapping.internal_method_name
            ):
                print(
                    "Basic game plugin from {} is missing {} property.".format(
                        self._fromName, basic_mapping.exposed_name
                    ),
                    file=sys.stderr,
                )

    """
    Here IPlugin interface stuff.
    """

    def init(self, organizer):
        self._organizer = organizer
        return True

    def name(self):
        return self._name

    def author(self):
        return self._author

    def description(self):
        if self._description is None:
            return "Adds basic support for game {}.".format(self.gameName())
        return self._description

    def version(self):
        return self._version

    def isActive(self):
        return True

    def settings(self):
        return []

    def gameName(self):
        return self._gameName

    def gameShortName(self):
        return self._gameShortName

    def gameIcon(self):
        return mobase.getIconForExecutable(
            self.gameDirectory().absoluteFilePath(self.binaryName())
        )

    def validShortNames(self):
        return []

    def gameNexusName(self):
        if self._gameNexusName is None:
            return self.gameShortName()
        return self._gameNexusName

    def nexusModOrganizerID(self):
        return 0

    def nexusGameID(self):
        return 0

    def steamAPPId(self):
        return self._steamAPPId

    def binaryName(self):
        return self._binaryName

    def getLauncherName(self):
        return self._launcherName

    def executables(self):
        return [
            mobase.ExecutableInfo(
                self.gameName(),
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            )
        ]

    def savegameExtension(self):
        return self._savegameExtension

    def savegameSEExtension(self):
        return ""

    def initializeProfile(self, path, settings):
        pass

    def primarySources(self):
        return []

    def primaryPlugins(self):
        return []

    def gameVariants(self):
        return []

    def setGameVariant(self, variantStr):
        pass

    def gameVersion(self):
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

    def isInstalled(self):
        return False

    def gameDirectory(self):
        """
        @return directory (QDir) to the game installation.
        """
        return QDir(self._gamePath)

    def dataDirectory(self):
        return QDir(self.gameDirectory().absoluteFilePath(self._dataDirectory))

    def setGamePath(self, pathStr):
        self._gamePath = pathStr

    def documentsDirectory(self):
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

        return None

    def savesDirectory(self):
        return self.documentsDirectory()

    def _featureList(self):
        return self._featureMap
