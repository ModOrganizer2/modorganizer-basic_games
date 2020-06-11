# Mod Organizer 2 - Simple Games Plugin

Mod Organizer 2 meta-plugin to make creating game plugins easier and faster.

## Why?

In order to create a MO2 game plugin, one must implements the `IPluginGame` interface,
but the interface contains a lot of things that most games do not require.

The goal of this meta-plugin is to load create plugins for "simple" games by simply
providing a `.ini` file or a very simply python class.

## How to install?

Download [the archive](https://github.com/Holt59/modorganizer-basic_games/archive/master.zip)
and extract it directly into your MO2 `plugins` folder.

**Important:** Extract the *folder* in your `plugins` folder, not the individual files. Your
`plugins` folder should look like this:

```
dlls/
plugins/
  data/
  modorganizer-basic_games-master/
    games/
      __init__.py
      ...
    __init__.py
    basic_game.py
    ...
  bsa_extractor.dll
  ...
ModOrganizer.exe
```

You can rename `modorganizer-basic_games-master` to whatever you want (e.g., `basic_games`).

## How to add a new game?

You can either provide a python class or a `.ini` file.

### Using a `.ini` file

You simply need to put your `.ini` file in games with the following content:

```ini
[DEFAULT]
# Name of the plugin (avoid space, whatever, ...):
Name=Witcher 3 Support Plugin

# Your name or username:
Author=Holt59

# Version of the plugin - Does not really make sense for .ini:
Version=1.0.0

# Name of the game, as you want it displayed by MO2:
GameName=The Witcher 3

# Short name of the game, used, e.g., for nexus:
GameShortName=witcher3

# Path to the executable, relative to the game folder:
GameBinary=bin/x64/witcher3.exe

# Name of the folder containing the data, relative to the game folder:
GameDataPath=mods

# Savegame extensions for the game:
GameSaveExtension=sav
```

### Using a Python file

You need to create a class that inherits `BasicGame` and put it in a `.py` file in `games`. Below is
an example for The Witcher 3:

```python
# -*- encoding: utf-8 -*-

from PyQt5.QtCore import QDir


from ..basic_game import BasicGame


class Witcher3Game(BasicGame):

    Name: str = "Witcher 3 Support Plugin"
    Author: str = "Holt59"
    Version: str = "1.0.0a"

    GameName: str = "The Witcher 3"
    GameShortName: str = "witcher3"
    GameBinary: str = "bin/x64/witcher3.exe"
    GameDataPath: str = "Mods"
    GameSaveExtension: str = "sav"

    def steamAPPId(self):
        return "292030"

    def savesDirectory(self):
        return QDir(self.documentsDirectory().absoluteFilePath("gamesaves"))
```

`BasicGame` inherits `IPluginGame` so you can override methods if you need to.
Each attribute you provide corresponds to a method (e.g., `Version` corresponds
to the `version` method). If you override the method, you do not have to provide
the attribute:

```python
class Witcher3Game(BasicGame):

    Name: str = "Witcher 3 Support Plugin"
    Author: str = "Holt59"

    GameName: str = "The Witcher 3"
    GameShortName: str = "witcher3"
    GameBinary: str = "bin/x64/witcher3.exe"
    GameDataPath: str = "Mods"
    GameSaveExtension: str = "sav"

    def version(self):
        # Don't forget to import mobase!
        return mobase.VersionInfo(1, 0, 0, mobase.ReleaseType.final)

    def steamAPPId(self):
        return "292030"

    def savesDirectory(self):
        return QDir(self.documentsDirectory().absoluteFilePath("gamesaves"))
```

### List of valid keys

If the column `Ini` is empty, it means it only accepts a basic string.

| Name | `IPluginGame` method | Python | Ini |
|------|----------------------|--------|-----|
| Name | `name` | `str` | |
| Author | `author` | `str` | |
| Version | `version` | `str` or `mobase.VersionInfo` | |
| Description (Optional) | `description` | `str` | `str` |
| GameName | `gameName` | `str` | |
| GameShortName | `gameShortName` | `str` | |
| GameNexusName (Optional) | `gameNexusName` | `str` | |
| GameValidShortNames (Optional) | `validShortNames` | `List[str]` or comma-separated list of values | comma-separated list of values |
| GameNexusId (Optional) | `nexusGameID` | `str` or `int` | |
| GameBinary | `binaryName` | `str` | |
| GameLauncher (Optional) | `getLauncherName` | `str` | |
| GameDataPath - Relative to game folder| `dataDirectory` | | |
| GameSaveExtension (Optional) | `savegameExtension` | `str` | |
| GameSteamId (Optional) | `steamAPPId` | `str` | |
