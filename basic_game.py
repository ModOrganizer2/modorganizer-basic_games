# -*- encoding: utf-8 -*-

import sys
import typing

from PyQt5.QtCore import QDir, QFileInfo, QStandardPaths

import mobase


class BasicGame(mobase.IPluginGame):

    """ This class implements some methods from mobase.IPluginGame
    to make it easier to create game plugins without having to implement
    all the methods of mobase.IPluginGame. """

    # List of fields that can be provided by child class:
    Name: str
    Author: str
    Version: str

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
    _gameName: str
    _gameShortName: str
    _binaryName: str
    _dataDirectory: str
    _savegameExtension: str

    # Match the name of the public attribute (from child class), to the
    # name of the protected attribute and the corresponding function:
    NAME_MAPPING = [
        ["Name", "name"],
        ["Author", "author"],
        ["Version", "version"],
        ["GameName", "gameName"],
        ["GameShortName", "gameShortName"],
        ["GameBinary", "binaryName"],
        ["GameDataPath", "dataDirectory"],
        ["GameSaveExtension", "savegameExtension"],
    ]

    def __init__(self):
        super(BasicGame, self).__init__()

        #         if not hasattr(self, "_fromName"):
        self._fromName = self.__class__.__name__

        # We init the member and check that everything is provided:
        for pub, prt in self.NAME_MAPPING:
            if hasattr(self, pub):
                value = getattr(self, pub)
                if pub == "Version":
                    value = mobase.VersionInfo(value)
                setattr(self, "_" + prt, value)
            elif getattr(self, prt) is getattr(BasicGame, prt):
                print(
                    "Basic game plugin from {} is missing {} property.".format(
                        self._fromName, pub
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
        return "Adds basic support for game {}.".format(self.gameName())

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
        return ""

    def nexusModOrganizerID(self):
        return 0

    def nexusGameID(self):
        return 0

    def steamAPPId(self):
        return ""

    def binaryName(self):
        return self._binaryName

    def getLauncherName(self):
        return ""

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
        pversion = mobase.getProductVersion(
            self.gameDirectory().absoluteFilePath(self.binaryName())
        )
        if not pversion:
            pversion = mobase.getFileVersion(
                self.gameDirectory().absoluteFilePath(self.binaryName())
            )
        return pversion

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
