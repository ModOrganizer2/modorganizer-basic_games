import os
import mobase

from PyQt6.QtCore import QDir
from ..basic_game import BasicGame

class Stalker2Game(BasicGame):

    # Open to contribution, take this plugin and expand on it as you please. Consider sharing on the MO2 GitHub if a more advanced version is made.
    Name = "S.T.A.L.K.E.R. 2 Heart of Chornobyl Support Plugin"
    Author = "MO2"
    Version = "0.1.0"

    GameName = "S.T.A.L.K.E.R. 2 Heart of Chornobyl"
    GameShortName = "stalker2heartofchornobyl"
    GameNexusName = "stalker2heartofchornobyl"
    GameBinary = "Stalker2.exe"
    GameDataPath = "Stalker2\Content\Paks\~mods"
    GameDocumentsDirectory = "%USERPROFILE%\AppData\Local\Stalker2\Saved"
    GameSaveExtension = "sav"
    GameSteamId = 1643320

    def savesDirectory(self):
        return QDir(self.documentsDirectory().absoluteFilePath("STEAM\SaveGames\Data"))
    
    # Snippet taken from the Kingdom Come Deliverance plugin
    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        # Create the mods directory if it doesn't exist
        modsPath = self.dataDirectory().absolutePath()
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)

        super().initializeProfile(directory, settings)
