# -*- encoding: utf-8 -*-

import struct

from PyQt5.QtGui import QImage

import mobase

from ..basic_game import BasicGame
from ..basic_features import BasicGameSaveGameInfo


class DarkMessiahOfMightAndMagicGame(BasicGame):
    Name = "Dark Messiah of Might and Magic Support Plugin"
    Author = "Holt59"
    Version = "0.1.0"

    GameName = "Dark Messiah of Might & Magic"
    GameShortName = "darkmessiahofmightandmagic"
    GameNexusName = "darkmessiahofmightandmagic"
    GameNexusId = 628
    GameSteamId = 2100
    GameBinary = "mm.exe"
    GameDataPath = "mm"

    GameDocumentsDirectory = "%GAME_PATH%/mm"
    GameSavesDirectory = "%GAME_PATH%/mm/SAVE"
    GameSaveExtension = "sav"

    def _read_save_tga(self, filename):
        # Qt TGA reader does not work for TGA, I hope that all files
        # have the same format:
        with open(filename.replace(".sav", ".tga"), "rb") as fp:
            data = fp.read()
        _, _, w, h, bpp, _ = struct.unpack("<HHHHBB", data[8:18])
        if bpp != 24:
            return None
        return QImage(data[18:], w, h, QImage.Format_RGB888)

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        self._featureMap[mobase.SaveGameInfo] = BasicGameSaveGameInfo(
            self._read_save_tga
        )
        return True
