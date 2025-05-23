
# ModOrganizer 2 - Basic Games - How to Contribute?

## How to add a new game?

You can create a plugin by providing a python class in the `games` folder.

**Note:** If your game plugin does not load properly, you should set the log level
to debug and look at the `mo_interface.log` file.

You need to create a class that inherits `BasicGame` and put it in a `game_XX.py` in `games`.
Below is an example for The Witcher 3 (see also [games/game_witcher3.py](games/game_witcher3.py)):

```python
from PyQt6.QtCore import QDir
from ..basic_game import BasicGame


class Witcher3Game(BasicGame):

    Name = "Witcher 3 Support Plugin"
    Author = "Holt59"
    Version = "1.0.0a"

    GameName = "The Witcher 3"
    GameShortName = "witcher3"
    GameBinary = "bin/x64/witcher3.exe"
    GameDataPath = "Mods"
    GameSaveExtension = "sav"
    GameSteamId = 292030

    def savesDirectory(self):
        return QDir(self.documentsDirectory().absoluteFilePath("gamesaves"))
```

`BasicGame` inherits `IPluginGame` so you can override methods if you need to.
Each attribute you provide corresponds to a method (e.g., `Version` corresponds
to the `version` method, see the table below). If you override the method, you do
not have to provide the attribute:

```python
from PyQt6.QtCore import QDir
from ..basic_game import BasicGame

import mobase


class Witcher3Game(BasicGame):

    Name = "Witcher 3 Support Plugin"
    Author = "Holt59"

    GameName = "The Witcher 3"
    GameShortName = "witcher3"
    GameBinary = "bin/x64/witcher3.exe"
    GameDataPath = "Mods"
    GameSaveExtension = "sav"
    GameSteamId = 292030

    def version(self):
        # Don't forget to import mobase!
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.final)

    def savesDirectory(self):
        return QDir(self.documentsDirectory().absoluteFilePath("gamesaves"))
```

### List of valid keys

| Name | Description | `IPluginGame` method | Python |
|------|-------------|----------------------|--------|
| Name | Name of the plugin | `name` | `str` |
| Author | Author of the plugin | `author` | `str` |
| Version | Version of the plugin | `version` | `str` or `mobase.VersionInfo` |
| Description| Description (Optional) | `description` | `str` |
| GameName | Name of the game, as displayed by MO2 | `gameName` | `str` |
| GameShortName | Short name of the game | `gameShortName` | `str` |
| GameNexusName| Nexus name of the game (Optional, default to `GameShortName`) | `gameNexusName` | `str` |
| GameValidShortNames | Other valid short names (Optional) | `validShortNames` | `List[str]` or comma-separated list of values |
| GameNexusId | Nexus ID of the game (Optional) | `nexusGameID` | `str` or `int` |
| GameBinary | Name of the game executable, relative to the game path | `binaryName` | `str` |
| GameLauncher | Name of the game launcher, relative to the game path  (Optional) | `getLauncherName` | `str` |
| GameDataPath | Name of the folder containing mods, relative to game folder| `dataDirectory` | |
| GameDocumentsDirectory | Documents directory (Optional) | `documentsDirectory` | `str` or `QDir` |
| GameIniFiles | Config files in documents, for profile specific config (Optional) | `iniFiles` | `str` or `List[str]` |
| GameSavesDirectory | Directory containing saves (Optional, default to `GameDocumentsDirectory`) | `savesDirectory` | `str` or `QDir` |
| GameSaveExtension | Save file extension (Optional) `savegameExtension` | `str` |
| GameSteamId | Steam ID of the game (Optional) | `steamAPPId` | `List[str]` or `str` or `int` |
| GameGogId | GOG ID of the game (Optional) | `gogAPPId` | `List[str]` or `str` or `int` |
| GameOriginManifestIds | Origin Manifest ID of the game (Optional) | `originManifestIds` | `List[str]` or `str` |
| GameOriginWatcherExecutables | Executables to watch for Origin DRM (Optional) | `originWatcherExecutables` | `List[str]` or `str` |
| GameEpicId | Epic ID (`AppName`) of the game (Optional) | `epicAPPId` | `List[str]` or `str` |
| GameEaDesktopId | EA Desktop ID of the game (Optional) | `eaDesktopContentId` | `List[str]` or `str` or `int` |

You can use the following variables for `str`:

- `%DOCUMENTS%` will be replaced by the standard *Documents* folder.
- `%GAME_PATH%` will be replaced by the path to the game folder.
- `%GAME_DOCUMENTS%` will be replaced by the value of `GameDocumentsDirectory`.

## Extra features

The meta-plugin provides some useful extra feature:

1. **Automatic Steam, GOG, Origin, Epic Games and EA Desktop detection:** If you provide
  Steam, GOG, Origin or Epic IDs for the game (via `GameSteamId`, `GameGogId`,
  `GameOriginManifestIds`, `GameEpicId` or `GameEaDesktopId`), the game will be listed
  in the list of available games when creating a new MO2 instance (if the game is
  installed via Steam, GOG, Origin, Epic Games / Legendary or EA Desktop).
2. **Basic save game preview / metadata** (Python): If you can easily obtain a picture
  (file) and/or metadata (like from json) for any saves, you can provide basic save-game
  preview by using the `BasicGameSaveGameInfo`. See
  [games/game_witcher3.py](games/game_witcher3.py) and
  [games/game_bladeandsorcery.py](games/game_bladeandsorcery.py) for more details.
3. **Basic local save games** (Python): profile specific save games, as in [games/game_valheim.py](games/game_valheim.py).
4. **Basic mod data checker** (Python):
  Check and fix different mod archive layouts for an automatic installation with the proper
  file structure, using simple (glob) patterns via `BasicModDataChecker`.
  See [games/game_valheim.py](games/game_valheim.py) and [game_subnautica.py](games/game_subnautica.py) for an example.

Game IDs can be found here:

- For Steam on [Steam Database](https://steamdb.info/)
- For GOG on [GOG Database](https://www.gogdb.org/)
- For Origin from `C:\ProgramData\Origin\LocalContent` (.mfst files)
- For Epic Games (`AppName`) from:
  - `C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests\` (.item files)
  - or `C:\ProgramData\Epic\EpicGamesLauncher\UnrealEngineLauncher\LauncherInstalled.dat`
  - or [Unofficial EGS ID DB](https://erri120.github.io/egs-db/)
- For Legendary (alt. Epic launcher) via command `legendary list-games`
    or from: `%USERPROFILE%\.config\legendary\installed.json`
- For EA Desktop from `<EA Games install location>\<game title>\__Installer\installerdata.xml`

## Contribute

We recommend using a dedicated Python environment to write a new basic game plugins.

1. Install the required version of Python - Currently Python 3.12 (MO2 2.5).
2. Remove the repository at `${MO2_INSTALL}/plugins/basic_games`.
3. Clone this repository at the location of the old plugin (
  `${MO2_INSTALL}/plugins/basic_games`).
4. Place yourself inside the cloned folder and:

  ```bash
  # create a virtual environment (recommended)
  py -3.12 -m venv .\venv
  .\venv\scripts\Activate.ps1

  # "install" poetry and the development package
  pip install poetry
  poetry install
  ```
