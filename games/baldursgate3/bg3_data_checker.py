from pathlib import Path

import mobase

from ...basic_features import BasicModDataChecker, GlobPatterns, utils
from . import bg3_utils


class BG3ModDataChecker(BasicModDataChecker):
    def __init__(self):
        super().__init__(
            GlobPatterns(
                valid=[
                    "*.pak",
                    str(Path("Mods") / "*.pak"),  # standard mods
                    "bin",  # native mods / Script Extender
                    "Script Extender",  # mods which are configured via jsons in this folder
                    "Data",  # loose file mods
                ]
                + [str(Path("*") / f) for f in bg3_utils.loose_file_folders],
                move={
                    "Root/": "",  # root builder not needed
                    "*.dll": "bin/",
                    "ScriptExtenderSettings.json": "bin/",
                }
                | {f: "Data/" for f in bg3_utils.loose_file_folders},
                delete=["info.json", "*.txt"],
            )
        )

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        invalid, valid, fixable = (
            mobase.ModDataChecker.INVALID,
            mobase.ModDataChecker.VALID,
            mobase.ModDataChecker.FIXABLE,
        )
        rank = (invalid, valid, fixable).index
        status = invalid
        rp = self._regex_patterns
        for entry in filetree:
            name = entry.name().casefold()
            if rp.unfold.match(name):
                if utils.is_directory(entry):
                    status = max(status, self.dataLooksValid(entry), key=rank)
                else:
                    status = invalid
                    break
            elif rp.valid.match(name):
                status = max(status, valid, key=rank)
            elif isinstance(entry, mobase.IFileTree):
                if all(rp.valid.match(e.pathFrom(filetree)) for e in entry):
                    status = max(status, valid, key=rank)
            elif rp.delete.match(name) or rp.move_match(name) is not None:
                status = fixable
            else:
                status = invalid
                break
        return status
