import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from xml.etree import ElementTree

sys.modules.setdefault("mobase", MagicMock())

from games.baldursgate3 import bg3_utils  # noqa: E402


class NodeStringTest(unittest.TestCase):
    def test_special_characters_round_trip(self):
        name = """Tom & Jerry's <"Best"> Mod"""
        node = bg3_utils.get_node_string(folder=name, name=name, uuid="u")
        attrs = {
            a.get("id"): a.get("value")
            for a in ElementTree.fromstring(node).iter("attribute")
        }
        self.assertEqual((attrs["Folder"], attrs["Name"]), (name, name))


class ProfilePathTest(unittest.TestCase):
    def test_modsettings_path_follows_profile_switch(self):
        with tempfile.TemporaryDirectory() as tmp:
            organizer = MagicMock()
            utils = bg3_utils.BG3Utils("Baldur's Gate 3 Plugin")
            utils.init(organizer)
            for profile in ("a", "b"):
                organizer.profilePath.return_value = str(Path(tmp, profile))
                self.assertEqual(
                    utils.modsettings_path, Path(tmp, profile, "modsettings.lsx")
                )
