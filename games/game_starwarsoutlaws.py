"""
  This plugin references the correct Steam ID. I do not have the game on Steam, 
  I have it on Ubi Connect, and it will silently fail to launch if the Ubi
  launcher is not open when you press Play in MO
"""

import mobase

from ..basic_game import BasicGame
from pathlib      import Path


class StarWarsOutlawsGame(BasicGame):
    Name = "Star Wars Outlaws"
    Author = "Bladehawke"
    Version = "1.1.0"

    GameName = "Star Wars Outlaws"
    GameShortName = "StarWarsOutlaws"
    GameNexusName = "starwarsoutlaws"
    GameSteamId = 2842040
    GameBinary = "Outlaws.exe"
    GameDataPath = ""
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Star-Wars-Outlaws"
    )

    _forced_libraries = ["version.dll", "dinput8.dll"] # Snowdrop and Raindrop mod loaders (Do *NOT* use both at the same time)
    
    def executables(self) -> list[mobase.ExecutableInfo]:
        game_name = self.gameName()
        game_dir = self.gameDirectory()
        bin_path = game_dir.absoluteFilePath(self.binaryName())
        return [
            mobase.ExecutableInfo(
                game_name,
                bin_path,
            )
        ]

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        exe = Path(self.binaryName()).name
        return [
            mobase.ExecutableForcedLoadSetting(exe, lib).withEnabled(True)
            for lib in self._forced_libraries
        ]