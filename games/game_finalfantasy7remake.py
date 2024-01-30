import math
import mobase
from typing import List

from ..basic_game import BasicGame


class FinalFantasy7RemakeGame(BasicGame, mobase.IPluginFileMapper):
    Name = "Final Fantasy VII Remake Support Plugin"
    Author = "TheUnlocked"
    Version = "1.0.0"

    GameName = "Final Fantasy VII Remake"
    GameShortName = "finalfantasy7remake"
    GameNexusName = "finalfantasy7remake"
    GameSteamId = 1462040
    GameBinary = "ff7remake.exe"
    GameSaveExtension = "sav"
    # This is a placeholder. In order to properly apply load order to mods, custom mapping is used below.
    GameDataPath = "_ROOT"

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)

    def init(self, organizer: mobase.IOrganizer):
        return BasicGame.init(self, organizer)

    def _modsPath(self):
        """The directory path of where .pak files from mods should go"""
        return self.gameDirectory().absolutePath() + "/End/Content/Paks/~mods"

    def mappings(self) -> List[mobase.Mapping]:
        mods = self._organizer.modList().allModsByProfilePriority()
        pak_priority_digits = math.floor(math.log10(len(mods))) + 1

        def create_mod_mappings(
            mod: mobase.IModInterface, priority: int
        ) -> List[mobase.Mapping]:
            # UE4 loads paks in alphabetical order, so we prefix the paks with their priority
            pak_prefix = str(priority).zfill(pak_priority_digits) + "_"

            custom_mappings: List[mobase.Mapping] = []

            def file_visitor(
                file_name: str, entry: mobase.FileTreeEntry
            ) -> mobase.IFileTree.WalkReturn:
                src_path = mod.absolutePath() + "/" + entry.path()

                if entry.hasSuffix("pak"):
                    dest_path = self._modsPath() + "/" + pak_prefix + entry.path()
                else:
                    dest_path = self._modsPath() + "/" + entry.path()

                custom_mappings.append(
                    mobase.Mapping(
                        src_path,
                        dest_path,
                        False,
                    )
                )

                return mobase.IFileTree.WalkReturn.CONTINUE

            mod.fileTree().walk(file_visitor)
            return custom_mappings

        return [
            # Not applying load order modifications to overwrites is OK
            # since the UX is better this way and it will generally work out anyways
            mobase.Mapping(
                self._organizer.overwritePath(),
                self._modsPath(),
                True,
                True,
            )
        ] + [
            mapping
            for i, mod_name in enumerate(mods)
            for mapping in create_mod_mappings(
                self._organizer.modList().getMod(mod_name), i
            )
        ]
