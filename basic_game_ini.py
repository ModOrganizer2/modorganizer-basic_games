# -*- encoding: utf-8 -*-

import configparser
import os

import mobase
from PyQt6.QtCore import QDir

from .basic_features import BasicGameSaveGameInfo, BasicLocalSavegames
from .basic_game import BasicGame


class BasicIniGame(BasicGame):
    def __init__(self, path: str):
        # Set the _fromName to get more "correct" errors:
        self._fromName = os.path.basename(path)

        # Read the file:
        config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation()
        )
        config.optionxform = str  # type: ignore
        config.read(path)

        # Fill the class with values:
        main_section = (
            config["BasicGame"] if "BasicGame" in config else config["DEFAULT"]
        )
        for k, v in main_section.items():
            setattr(self, k, v)

        super().__init__()

        # Add features
        if "Features" in config:
            features = config["Features"]
            # BasicLocalSavegames
            try:
                # LocalSavegames = True
                if features.getboolean("LocalSavegames"):
                    self._featureMap[mobase.LocalSavegames] = BasicLocalSavegames(
                        self.savesDirectory()
                    )
            except ValueError:
                # LocalSavegames = path
                self._featureMap[mobase.LocalSavegames] = BasicLocalSavegames(
                    QDir(features["LocalSavegames"])
                )
            except KeyError:
                pass

            # SaveGamePreview = BasicGameSaveGameInfo
            if preview := features.get("SaveGamePreview"):
                self._featureMap[mobase.SaveGameInfo] = BasicGameSaveGameInfo(
                    get_preview=lambda p: p / preview
                )
