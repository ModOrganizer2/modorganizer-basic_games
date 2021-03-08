from ..basic_game import BasicGame


class MSFS2020Game(BasicGame):

    Name = "Microsoft Flight Simulator 2020 Support Plugin"
    Author = "Deorder"
    Version = "0.0.1"

    GameName = "Microsoft Flight Simulator 2020"
    GameShortName = "msfs2020"
    GameBinary = r"FlightSimulator.exe"
    GameDataPath = r"%USERPROFILE%\AppData\Roaming\Microsoft Flight Simulator\Packages"
    GameSteamId = [1250410]
