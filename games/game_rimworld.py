# -*- encoding: utf-8 -*-

import mobase

from ..basic_game import BasicGame

#TODO: Better savegame and settings integration.

"""
class RimworldLocalSavegames(mobase.LocalSavegames):

    def __init__(self):
        super().__init__()

    def mappings(self, profile_save_dir: PyQt5.QtCore.QDir) -> List["Mapping"]:
        #TODO: Figure out what mappings I need to find exactly
    
    def prepareProfile(self, profile: "IProfile") -> bool:
        #TODO: Basically all of the following, just tweaked to work with Rimworld.
        # https://github.com/ModOrganizer2/modorganizer-game_gamebryo/blob/498b10696f3a9c7383379c7d99eb921032629434/src/gamebryo/gamebryolocalsavegames.cpp#L51
"""

class RimworldGame(BasicGame):

    Name = "RimWorld Support Plugin"
    Author = "Luca/EzioTheDeadPoet"
    Version = "1.0.0a"
    Description = "This is very alpha stage and therefore relies on you to make a \"mod\" that stores the saves and config files and adding the launch argument \"-savedatafolder=Mods/ConfigAndSavesFolderName\" to the Rimworld executable. Otherwise you get no MO2 instance specific saves and configs."

    GameName = "RimWorld"
    GameShortName = "rimworld"
    GameNexusName = "rimworld"
    GameSteamId = 294100
    GameGogId = 1094900565
    GameBinary = "RimWorldWin64.exe"
    GameDataPath = "Mods"