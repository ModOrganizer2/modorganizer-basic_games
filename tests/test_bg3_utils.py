import sys
import unittest
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
