import importlib
import sys
import types
import unittest
from enum import IntEnum
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

mobase: Any = sys.modules.setdefault("mobase", MagicMock())


class _ModDataChecker:
    class CheckReturn(IntEnum):
        INVALID = 0
        FIXABLE = 1
        VALID = 2

    INVALID = CheckReturn.INVALID
    FIXABLE = CheckReturn.FIXABLE
    VALID = CheckReturn.VALID


class _IFileTree:
    def __init__(self, name: str, children: list[MagicMock]) -> None:
        self._name, self._children = name, children
        for c in children:
            c.pathFrom.return_value = f"{name}/{c.name()}"

    def name(self) -> str:
        return self._name

    def isDir(self) -> bool:
        return True

    def __iter__(self):
        return iter(self._children)


mobase.ModDataChecker = _ModDataChecker
mobase.IFileTree = _IFileTree

# The repo root is a package, so the module's relative imports need a parent package name.
_pkg = types.ModuleType("basic_games")
_pkg.__path__ = [str(Path(__file__).resolve().parents[1])]
sys.modules.setdefault("basic_games", _pkg)

BG3ModDataChecker = importlib.import_module(
    "basic_games.games.baldursgate3.bg3_data_checker"
).BG3ModDataChecker


def _file(name: str) -> MagicMock:
    entry = MagicMock()
    entry.name.return_value = name
    entry.isDir.return_value = False
    return entry


class DataLooksValidTest(unittest.TestCase):
    def test_fixable_entry_survives_later_valid_directory(self):
        root = [_file("info.json"), _IFileTree("Extra", [_file("x.pak")])]
        self.assertEqual(
            BG3ModDataChecker().dataLooksValid(root),  # type: ignore[arg-type]
            _ModDataChecker.FIXABLE,
        )


if __name__ == "__main__":
    unittest.main()
