# -*- encoding: utf-8 -*-

from ..basic_game import BasicGame


class NehrimGame(BasicGame):
    """
    This is not a fully implemented plugin as all of the Nehrim functionality
    is essentially covered by the Oblivion plugin. This is designed to be a
    minimum viable implementation to allow the Oblivion plugin to download
    Nehrim mods.
    """

    Name = "Nehrim Support Plugin"
    Author = "LostDragonist"
    Version = "1.0.0"

    GameName = "Nehrim (use Oblivion instead)"
    GameShortName = "nehrim"
    GameNexusName = "nehrim"
    GameNexusId = 3312
    GameBinary = "THIS_IS_NOT_A_REAL_GAME_PLUGIN"
    GameDataPath = "THIS_IS_NOT_A_REAL_GAME_PLUGIN"
