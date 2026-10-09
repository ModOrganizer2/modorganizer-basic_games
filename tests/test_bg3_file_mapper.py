# pyright: reportPrivateUsage=false, reportAbstractUsage=false
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

mobase: Any = sys.modules.setdefault("mobase", MagicMock())
mobase.IPluginFileMapper = object
mobase.IPluginTool = type("IPluginTool", (), {})
mobase.IPlugin = type("IPlugin", (), {})
mobase.Mapping = SimpleNamespace

from games.baldursgate3 import bg3_file_mapper  # noqa: E402
from games.baldursgate3.plugins import convert_jsons_to_yaml_plugin  # noqa: E402


class ConvertTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_yaml_to_json_skips_bad_file(self):
        (self.tmp / "bad.yaml").write_text("a: [", encoding="utf-8")
        (self.tmp / "good.yml").write_text("name: Ünï\n", encoding="utf-8")
        utils = MagicMock(convert_yamls_to_json=True)
        mapper = bg3_file_mapper.BG3FileMapper(utils, MagicMock())
        mapper.map_files([], self.tmp, only_convert=True)
        good = self.tmp / "good.json"
        self.assertEqual(json.loads(good.read_text(encoding="utf-8")), {"name": "Ünï"})
        self.assertFalse((self.tmp / "bad.json").exists())

    def test_json_to_yaml_skips_bad_file(self):
        (self.tmp / "bad.json").write_text("{", encoding="utf-8")
        (self.tmp / "good.json").write_text('{"name": "Ünï"}', encoding="utf-8")
        convert_jsons_to_yaml_plugin._convert_jsons_in_dir_to_yaml(self.tmp)
        self.assertIn("Ünï", (self.tmp / "good.yaml").read_text(encoding="utf-8"))
        self.assertFalse((self.tmp / "bad.yaml").exists())


class CancelTest(unittest.TestCase):
    def test_cancel_keeps_modsettings_mapping(self):
        tmp = Path(tempfile.mkdtemp())
        modsettings = tmp / "modsettings.lsx"
        modsettings.touch()
        utils = MagicMock(convert_yamls_to_json=False, modsettings_path=modsettings)
        utils.active_mods.return_value = [MagicMock(absolutePath=lambda: str(tmp))]
        utils.create_progress_window.return_value.wasCanceled.return_value = True
        mapper = bg3_file_mapper.BG3FileMapper(
            utils, lambda: MagicMock(path=lambda: str(tmp / "docs"))
        )
        with patch.object(bg3_file_mapper, "QApplication"):
            sources = [m.source for m in mapper.mappings()]
        self.assertIn(str(modsettings), sources)


if __name__ == "__main__":
    unittest.main()
