from enum import IntEnum, auto

import mobase


class Content(IntEnum):
    PAK = auto()
    WORKSPACE = auto()
    NATIVE = auto()
    LOOSE_FILES = auto()
    SE_FILES = auto()


class BG3DataContent(mobase.ModDataContent):
    BG3_CONTENTS: list[tuple[Content, str, str, bool] | tuple[Content, str, str]] = [
        (Content.WORKSPACE, "Mod workspaces", ":/MO/gui/content/plugin"),
        (Content.PAK, "Paks", ":/MO/gui/content/geometries"),
        (Content.LOOSE_FILES, "Loose file override mods", ":/MO/gui/content/skse"),
        (Content.SE_FILES, "Script Extender Files", "", True),
        (Content.NATIVE, "Native DLL mods", ":/MO/gui/content/script"),
    ]

    def getAllContents(self) -> list[mobase.ModDataContent.Content]:
        return [
            mobase.ModDataContent.Content(id, name, icon, *filter_only)
            for id, name, icon, *filter_only in self.BG3_CONTENTS
        ]

    def getContentsFor(self, filetree: mobase.IFileTree) -> list[int]:
        contents: set[int] = set()
        for entry in filetree:
            if isinstance(entry, mobase.IFileTree):
                match entry.name().casefold():
                    case "Script Extender":
                        contents.add(Content.SE_FILES)
                    case "Data":
                        contents.add(Content.LOOSE_FILES)
                    case x if x.endswith(".pak"):
                        contents.add(Content.PAK)
                    case "Mods":
                        for e in entry:
                            if e.name().endswith(".pak"):
                                contents.add(Content.PAK)
                                break
                    case "bin":
                        contents.add(Content.NATIVE)
                    case _:
                        for e in entry:
                            match e.name().casefold():
                                case "Mods" | "Localization" | "ScriptExtender" | "Public" | "Generated":
                                    contents.add(Content.WORKSPACE)
                                    break
        return list(contents)
