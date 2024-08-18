import re
import mobase
from mobase import FileTreeEntry, IFileTree, ModDataChecker
from ..basic_features import BasicModDataChecker
from ..basic_game import BasicGame


_extention_pattern = re.compile("\\.(upk|umap|u|int|dll|exe)$", re.I)
_mapslot_pattern = re.compile("^Mapslot\\d\\d?\\.umap$", re.I)

_mod_dirs = {
    "Binaries".casefold(): "/",
    "WillowGame".casefold(): "/",
    "CookedPC".casefold(): "WillowGame/",
    "Localization".casefold(): "WillowGame/",
    "Maps".casefold(): "WillowGame/CookedPC/",
}

_slots_path = "WillowGame/CookedPC/Maps/MapSlots"


def _check_filetree(
    filetree: IFileTree | FileTreeEntry, recurse: bool
) -> ModDataChecker.CheckReturn:
    if filetree.isFile():
        if _extention_pattern.search(filetree.name()):
            if _mapslot_pattern.search(filetree.name()):
                return ModDataChecker.FIXABLE
            else:
                return ModDataChecker.INVALID
    elif recurse and isinstance(filetree, IFileTree):
        status = ModDataChecker.VALID
        for child in filetree:
            child_status = _check_filetree(child, True)
            if child_status is ModDataChecker.INVALID:
                return ModDataChecker.INVALID
            elif child_status is ModDataChecker.FIXABLE:
                status = ModDataChecker.FIXABLE
        return status

    return ModDataChecker.VALID


def _get_slotstree(roottree: IFileTree) -> IFileTree:
    slotstree: IFileTree | None = roottree.find(_slots_path)  # type: ignore
    if slotstree is None:
        slotstree = roottree.addDirectory(_slots_path)
    return slotstree


def _fix_mapslots(filetree: IFileTree, roottree: IFileTree) -> None:
    for child in filetree:
        if child.isDir() and isinstance(child, IFileTree):
            _fix_mapslots(child, roottree)
        elif _mapslot_pattern.search(child.name()):
            child.moveTo(_get_slotstree(roottree))


class Borderlands1ModDataChecker(BasicModDataChecker):
    def dataLooksValid(
        self, filetree: IFileTree
    ) -> ModDataChecker.CheckReturn:
        parent = filetree.parent()
        if parent:
            return self.dataLooksValid(parent)

        status = _check_filetree(filetree, False)
        if status is ModDataChecker.INVALID:
            return status

        slotstree = filetree.find(_slots_path)
        if slotstree is not None and not slotstree.isDir():
            return ModDataChecker.INVALID

        for child in filetree:
            if child.isDir():
                destination = _mod_dirs.get(child.name().casefold())
                if destination is None:
                    child_status = _check_filetree(child, True)
                    if child_status is ModDataChecker.INVALID:
                        return ModDataChecker.INVALID
                    elif child_status is ModDataChecker.FIXABLE:
                        status = ModDataChecker.FIXABLE
                elif destination != "/":
                    status = ModDataChecker.FIXABLE
            elif _mapslot_pattern.search(child.name()):
                status = ModDataChecker.FIXABLE
            elif _extention_pattern.search(child.name()):
                return ModDataChecker.INVALID
        return status

    def fix(self, filetree: IFileTree) -> IFileTree:
        for child in tuple(filetree):
            if child.isDir() and isinstance(child, IFileTree):
                destination = _mod_dirs.get(child.name().casefold())
                if destination is None:
                    _fix_mapslots(child, filetree)
                elif destination != "/":
                    filetree.move(child, destination)
            elif _mapslot_pattern.search(child.name()):
                child.moveTo(_get_slotstree(filetree))

        return filetree


class Borderlands1Game(BasicGame):
    Name = "Borderlands 1 Support Plugin"
    Author = "Miner Of Worlds, RedxYeti, mopioid"
    Version = "1.0.0"

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(Borderlands1ModDataChecker())
        return True

    GameName = "Borderlands"
    GameShortName = "Borderlands"
    GameNexusName = "Borderlands GOTY"
    GameSteamId = 8980
    GameBinary = "Binaries/Borderlands.exe"
    GameDataPath = "."
    GameSaveExtension = "sav"
    GameDocumentsDirectory = "%DOCUMENTS%/My Games/Borderlands/"
    GameSavesDirectory = "%GAME_DOCUMENTS%/savedata"
    GameIniFiles = "%GAME_DOCUMENTS%/WillowGame/Config"
