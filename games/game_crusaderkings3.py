from ..basic_game import BasicGame


class CrusaderKings3Game(BasicGame):
    
    Name = "Crusader Kings 3 Support Plugin"
    Author = "Cram42"
    Version = "0.1.0"

    GameName = "Crusader Kings 3"
    GameShortName = "crusaderkings3"
    GameBinary = "binaries/ck3.exe"
    GameDataPath = "%GAME_PATH%/game"
    GameDocumentsDirectory = "%DOCUMENTS%/Paradox Interactive/Crusader Kings III"
    GameSavesDirectory = "%GAME_DOCUMENTS%/save games"
    GameSaveExtension = "ck3"
    GameSteamId = 1158310

    def init(self, organizer):
        super().init(organizer)
        return True
