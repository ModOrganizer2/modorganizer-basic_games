# -*- encoding: utf-8 -*-

from typing import List, Optional

import mobase

from ..basic_game import BasicGame


class ZeusAndPoseidonModDataChecker(mobase.ModDataChecker):
    def __init__(self):
        super().__init__()

    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:

        folders: List[mobase.IFileTree] = []
        files: List[mobase.FileTreeEntry] = []

        for entry in tree:
            if isinstance(entry, mobase.IFileTree):
                folders.append(entry)
            else:
                files.append(entry)

        if len(folders) != 1:
            return mobase.ModDataChecker.INVALID

        folder = folders[0]
        pakfile = folder.name() + ".pak"
        if folder.exists(pakfile):
            if tree.exists(pakfile):
                return mobase.ModDataChecker.VALID
            else:
                return mobase.ModDataChecker.FIXABLE

        return mobase.ModDataChecker.INVALID

    def fix(self, tree: mobase.IFileTree) -> Optional[mobase.IFileTree]:
        if not isinstance(tree[0], mobase.IFileTree):
            return None
        entry = tree[0].find(tree[0].name() + ".pak")
        if entry is None:
            return None
        tree.copy(entry, "", mobase.IFileTree.InsertPolicy.FAIL_IF_EXISTS)
        return tree


class ZeusAndPoseidonGame(BasicGame):

    Name = "Zeus and Poseidon Support Plugin"
    Author = "Holt59"
    Version = "1.0.0a"

    GameName = "Zeus and Poseidon"
    GameShortName = "zeusandposeidon"  # No Nexus support
    GameSteamId = 566050
    GameGogId = 1207659039
    GameBinary = "Zeus.exe"
    GameDataPath = "Adventures"
    GameDocumentsDirectory = "%GAME_PATH%"
    GameSavesDirectory = "%GAME_PATH%/Save"
    GameSaveExtension = "sav"
    GameSupportURL = (
        r"https://github.com/ModOrganizer2/modorganizer-basic_games/wiki/"
        "Game:-Zeus%EF%BC%8BPoseidon"
    )

    def init(self, organizer: mobase.IOrganizer):
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = ZeusAndPoseidonModDataChecker()
        return True
