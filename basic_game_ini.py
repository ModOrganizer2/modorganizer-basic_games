# -*- encoding: utf-8 -*-

import configparser
import os

from .basic_game import BasicGame


class BasicIniGame(BasicGame):
    def __init__(self, path: str):
        # Set the _fromName to get more "correct" errors:
        self._fromName = os.path.basename(path)

        # Read the file:
        config = configparser.ConfigParser()
        config.optionxform = str  # type: ignore
        config.read(path)

        # Fill the class with values:
        main_section = (
            config["BasicGame"] if "BasicGame" in config else config["DEFAULT"]
        )
        for k, v in main_section.items():
            setattr(self, k, v)

        super().__init__()
