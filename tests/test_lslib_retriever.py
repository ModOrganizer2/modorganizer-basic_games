import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

sys.modules.setdefault("mobase", MagicMock())

from games.baldursgate3 import lslib_retriever  # noqa: E402


class ExtractTest(unittest.TestCase):
    def test_overwrites_existing_files_and_keeps_subfolders(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp)
            (tools / "Divine.exe").write_bytes(b"old")
            zip_path = tools / "lslib.zip"
            with zipfile.ZipFile(zip_path, "w") as z:
                z.writestr("Packed/Tools/", b"")
                z.writestr("Packed/Tools/Divine.exe", b"new")
                z.writestr("Packed/Tools/runtimes/win/x.dll", b"dll")
                z.writestr("Packed/Other/skip.txt", b"skip")
            utils = MagicMock(tools_dir=tools)
            utils.create_progress_window.return_value.wasCanceled.return_value = False
            retriever = lslib_retriever.LSLibRetriever(utils)
            self.assertTrue(retriever._extract(zip_path))  # pyright: ignore[reportPrivateUsage]
            self.assertEqual((tools / "Divine.exe").read_bytes(), b"new")
            self.assertEqual((tools / "runtimes/win/x.dll").read_bytes(), b"dll")
            self.assertFalse((tools / "skip.txt").exists())
            self.assertFalse((tools / "Packed").exists())
