# -*- encoding: utf-8 -*-

import glob
import importlib
import os
import site
import sys
import typing

from .basic_game import BasicGame
from .basic_game_ini import BasicIniGame

site.addsitedir(os.path.join(os.path.dirname(__file__), "lib"))


BasicGame.setup()


def createPlugins():

    # List of game class from python:
    game_plugins: typing.List[BasicGame] = []

    # We are going to list all game plugins:
    curpath = os.path.abspath(os.path.dirname(__file__))

    # List all the .ini files:
    for file in glob.glob(os.path.join(curpath, "games", "*.ini")):
        game_plugins.append(BasicIniGame(file))

    # List all the python plugins:
    for file in glob.glob(os.path.join(curpath, "games", "*.py")):
        module_p = os.path.relpath(file, os.path.join(curpath, "games"))
        if module_p == "__init__.py":
            continue

        # Import the module:
        try:
            module = importlib.import_module(".games." + module_p[:-3], __package__)
        except ImportError as e:
            print("Failed to import module {}: {}".format(module_p, e), file=sys.stderr)
        except Exception as e:
            print("Failed to import module {}: {}".format(module_p, e), file=sys.stderr)

        # Lookup game plugins:
        for name in dir(module):
            if hasattr(module, name):
                obj = getattr(module, name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BasicGame)
                    and obj is not BasicGame
                ):
                    try:
                        game_plugins.append(obj())
                    except Exception as e:
                        print(
                            "Failed to instantiate {}: {}".format(name, e),
                            file=sys.stderr,
                        )

    return game_plugins
