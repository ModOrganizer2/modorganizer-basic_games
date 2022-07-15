# -*- encoding: utf-8 -*-

import os
import configparser
from PyQt5.QtCore import QDir

from ..basic_game import BasicGame


class Fallout2Game(BasicGame):
    Name = "Fallout 2 - Support Plugin"
    Author = "mrowrpurr"
    Version = "0.1.0"

    GameName = "Fallout 2"
    GameShortName = "fallout2"
    GameNexusName = "fallout2"
    GameNexusId = 430
    GameSteamId = 38410
    GameGogId = 1440151285
    GameBinary = "fallout2HR.exe"
    GameDataPath = "%GAME_PATH%"
    GameDocumentsDirectory = "%GAME_PATH%"

    def iniFiles(self):
        return ["ddraw.ini", "f2_res.ini"]

    def updateFallout2cfg(self):
        # Update fallout2.cfg (.ini format) for game to run via Mod Organizer 2
        #
        # [system]
        # critter_dat=critter.dat <-- these paths must all be set to
        # critter_patches=data    <-- to absolute paths
        # master_dat=master.dat   <--
        # master_patches=data     <--
        game_directory = self.gameDirectory().absolutePath()
        fallout2_cfg_path = os.path.join(game_directory, "fallout2.cfg")
        config = configparser.ConfigParser()
        config.read(fallout2_cfg_path)
        config["system"]["critter_dat"] = os.path.join(game_directory, "critter.dat")
        config["system"]["critter_patches"] = os.path.join(game_directory, "data")
        config["system"]["master_dat"] = os.path.join(game_directory, "master.dat")
        config["system"]["master_patches"] = os.path.join(game_directory, "data")
        with open(fallout2_cfg_path, "w") as configfile:
            config.write(configfile)

    def initializeProfile(self, path: QDir, settings: int):
        # Update fallout2.cfg, if present
        game_directory = self.gameDirectory().absolutePath()
        fallout2_cfg_path = os.path.join(game_directory, "fallout2.cfg")
        if os.path.exists(fallout2_cfg_path):
            self.updateFallout2cfg()
        super().initializeProfile(path, settings)
