import mobase

from ..basic_game import BasicGame


class CrusaderKings3ModDataChecker(mobase.ModDataChecker):

    def findRealDescriptor(self, tree: mobase.IFileTree) -> mobase.FileTreeEntry:
        descriptor = tree.find("descriptor.mod", mobase.FileTreeEntry.FileTypes.FILE)
        if descriptor:
            return descriptor
        
        for entry in tree:
            if entry.isDir():
                descriptor = self.findRealDescriptor(entry)
                if descriptor:
                    return descriptor
        
        return None
    
    def findModDescriptor(self, tree: mobase.IFileTree) -> mobase.FileTreeEntry:
        for entry in tree:
            if entry.isFile():
                if entry.suffix() == "mod":
                    return entry
        
        for entry in tree:
            if entry.isDir():
                descriptor = self.findModDescriptor(entry)
                if descriptor:
                    return descriptor
        
        return None

    def validateModTree(self, tree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        for entry in tree:
            valid_items = self.validDirNames if entry.isDir() else self.validFileNames
            if not entry.name().casefold() in valid_items:
                return mobase.ModDataChecker.INVALID
        return mobase.ModDataChecker.VALID

    def validateArchiveTree(self, tree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        # Look for descriptor.mod
        descriptor = self.findRealDescriptor(tree)
        if descriptor:
            self.contentTree = descriptor.parent()
            return mobase.ModDataChecker.FIXABLE
        
        # Look for [modname].mod
        descriptor = self.findModDescriptor(tree)
        if descriptor:
            content_name = descriptor.name()[:-4]
            self.contentTree = descriptor.parent().find(content_name, mobase.FileTreeEntry.FileTypes.DIRECTORY)
            if self.contentTree:
                return mobase.ModDataChecker.FIXABLE
        
        # Invalid archive
        return mobase.ModDataChecker.INVALID

    def __init__(self):
        super().__init__()
        self.contentTree = None
        self.validDirNames = [
            "common",
            "content_source",
            "data_binding",
            "dlc",
            "dlc_metadata",
            "events",
            "fonts",
            "gfx",
            "gui",
            "history",
            "licenses",
            "localization",
            "map_data",
            "music",
            "notifications",
            "sound",
            "tests",
            "tools",
            "tweakergui_assets"
        ]
        self.validFileNames = []

    def dataLooksValid(self, tree: mobase.IFileTree) -> mobase.ModDataChecker.CheckReturn:
        # Normal mod tree check
        if self.validateModTree(tree) == mobase.ModDataChecker.VALID:
            return mobase.ModDataChecker.VALID
        
        # Archive check
        return self.validateArchiveTree(tree)
    
    def fix(self, tree: mobase.IFileTree) -> mobase.IFileTree:
        new_tree = tree.createOrphanTree("")
        for entry in self.contentTree:
            valid_names = self.validDirNames if entry.isDir() else self.validFileNames
            if entry.name().casefold() in valid_names:
                new_tree.copy(entry)
        return new_tree


class CrusaderKings3Game(BasicGame):
    
    Name = "Crusader Kings 3 Support Plugin"
    Author = "Cram42"
    Version = "0.1.0"

    GameName = "Crusader Kings 3"
    GameShortName = "crusaderkings3"
    GameBinary = "binaries/ck3.exe"
    GameDataPath = "%GAME_PATH%/game"
    GameDocumentsDirectory = "%DOCUMENTS%/Paradox Interactive/Crusader Kings III"
    GameSavesDirectory = "%GAME_DOCUMENTS%/save games"
    GameSaveExtension = "ck3"
    GameSteamId = 1158310

    def init(self, organizer):
        super().init(organizer)
        self._featureMap[mobase.ModDataChecker] = CrusaderKings3ModDataChecker()
        return True
