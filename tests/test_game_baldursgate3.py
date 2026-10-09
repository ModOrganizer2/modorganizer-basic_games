import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.modules.setdefault("mobase", MagicMock())

from games.baldursgate3 import bg3_utils  # noqa: E402


class RemoveEmptyDirsTest(unittest.TestCase):
    def test_removes_nested_empty_dirs_and_keeps_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a" / "b" / "c").mkdir(parents=True)
            (root / "z").mkdir()
            (root / "keep").mkdir()
            (root / "keep" / "f.txt").write_text("x")
            removed = bg3_utils.remove_empty_dirs(root)
            self.assertTrue(root.exists())
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["keep"])
            self.assertEqual(
                removed,
                {root / "a", root / "a" / "b", root / "a" / "b" / "c", root / "z"},
            )

    def test_keeps_empty_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(bg3_utils.remove_empty_dirs(Path(tmp)), set())
            self.assertTrue(Path(tmp).exists())


if __name__ == "__main__":
    unittest.main()
