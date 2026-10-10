import mobase

from ...basic_features import (
    BasicModDataChecker,
    GlobPatterns,
)
from ...basic_features.utils import is_directory


class FF12ModDataChecker(BasicModDataChecker):
    def __init__(self):
        super().__init__(
            GlobPatterns(
                unfold=["*"],
                delete=["*"],
                valid=["x64", "mods", "dxgi.dll", "dinput8.dll", "launcher.dll"],
                move={
                    "scripts": "x64/",
                    "modules": "x64/",
                    "gamedata": "mods/deploy/ff12data/",
                    "jsondata": "mods/deploy/ff12data/",
                    "prefetchdata": "mods/deploy/ff12data/",
                    "ps2data": "mods/deploy/ff12data/",
                    "ff12data": "mods/deploy/",
                },
            )
        )

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        status = mobase.ModDataChecker.VALID

        rp = self._regex_patterns
        for entry in filetree:
            name = entry.name().casefold()

            if rp.valid.match(name):
                if status is mobase.ModDataChecker.INVALID:
                    status = mobase.ModDataChecker.VALID

            elif rp.move_match(name):
                status = mobase.ModDataChecker.FIXABLE

            elif rp.unfold.match(name) and is_directory(entry):
                status = mobase.ModDataChecker.FIXABLE
                new_status = self.dataLooksValid(entry)
                if new_status is not mobase.ModDataChecker.VALID:
                    status = new_status

            elif rp.delete.match(name):
                status = mobase.ModDataChecker.FIXABLE

            else:
                status = mobase.ModDataChecker.INVALID
                break
        return status

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        rp = self._regex_patterns

        for entry in list(filetree):
            name = entry.name().casefold()

            if rp.valid.match(name):
                continue

            elif (move_key := rp.move_match(name)) is not None:
                target = self._file_patterns.move[move_key]
                filetree.move(entry, target)

            elif rp.unfold.match(name) and is_directory(entry):
                filetree.merge(entry)
                entry.detach()
                self.fix(filetree)

            elif rp.delete.match(name):
                entry.detach()

        return filetree
