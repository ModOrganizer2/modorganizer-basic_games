from enum import IntEnum, auto

import mobase


class Content(IntEnum):
    PLUGIN = auto()
    BSA = auto()
    PAK = auto()
    OBSE = auto()
    OBSE_FILES = auto()
    MOVIE = auto()
    UE4SS = auto()
    MAGIC_LOADER = auto()


class OblivionRemasteredDataContent(mobase.ModDataContent):
    OR_CONTENTS: list[tuple[Content, str, str, bool] | tuple[Content, str, str]] = [
        (Content.PLUGIN, "Plugins (ESM/ESP)", ":/MO/gui/content/plugin"),
        (Content.BSA, "Bethesda Archive", ":/MO/gui/content/bsa"),
        (Content.PAK, "Paks", ":/MO/gui/content/geometries"),
        (Content.OBSE, "Script Extender Plugin", ":/MO/gui/content/skse"),
        (Content.OBSE_FILES, "Script Extender Files", "", True),
        (Content.MOVIE, "Movies", ":/MO/gui/content/media"),
        (Content.UE4SS, "UE4SS Mods", ":/MO/gui/content/script"),
        (Content.MAGIC_LOADER, "Magic Loader Mod", ":/MO/gui/content/inifile"),
    ]

    def getAllContents(self) -> list[mobase.ModDataContent.Content]:
        return [
            mobase.ModDataContent.Content(id, name, icon, *filter_only)
            for id, name, icon, *filter_only in self.OR_CONTENTS
        ]

    def getContentsFor(self, filetree: mobase.IFileTree) -> list[int]:
        contents: set[int] = set()

        for entry in filetree:
            if isinstance(entry, mobase.IFileTree):
                match entry.name().casefold():
                    case "data":
                        for data_entry in entry:
                            if data_entry.isFile():
                                match data_entry.suffix().casefold():
                                    case "esm" | "esp":
                                        contents.add(Content.PLUGIN)
                                    case "bsa":
                                        contents.add(Content.BSA)
                                    case _:
                                        pass
                            else:
                                match data_entry.name().casefold():
                                    case "magicloader":
                                        contents.add(Content.MAGIC_LOADER)
                                    case _:
                                        pass
                    case "obse":
                        contents.add(Content.OBSE_FILES)
                        plugins_dir = entry.find("Plugins")
                        if isinstance(plugins_dir, mobase.IFileTree):
                            for plugin_entry in plugins_dir:
                                if plugin_entry.suffix().casefold() == "dll":
                                    contents.add(Content.OBSE)
                                    break
                    case "paks":
                        contents.add(Content.PAK)
                        for paks_entry in entry:
                            if isinstance(paks_entry, mobase.IFileTree):
                                if paks_entry.name().casefold() == "~mods":
                                    if paks_entry.find("MagicLoader"):
                                        contents.add(Content.MAGIC_LOADER)
                                if paks_entry.name().casefold() == "logicmods":
                                    contents.add(Content.UE4SS)
                    case "movies":
                        contents.add(Content.MOVIE)
                    case "ue4ss":
                        contents.add(Content.UE4SS)
                    case _:
                        pass

        return list(contents)
