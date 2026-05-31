import os
import re
import shutil
from enum import IntEnum, auto
from functools import cached_property
from pathlib import Path

from PyQt6.QtCore import QDir, QFileInfo

import mobase

from ..basic_features import BasicGameSaveGameInfo
from ..basic_game import BasicGame


class Content(IntEnum):
    IMAGE = auto()
    MUSIC = auto()
    SCRIPT = auto()
    SOUND = auto()
    STRING = auto()
    LEVEL = auto()


class ZumaModDataContent(mobase.ModDataContent):
    GAMECONTENTS: list[tuple[Content, str, str, bool] | tuple[Content, str, str]] = [
        (Content.IMAGE, "Textures", ":/MO/gui/content/texture"),
        (Content.MUSIC, "Music", ":/MO/gui/content/music"),
        (Content.SCRIPT, "Scripts", ":/MO/gui/content/script"),
        (Content.SOUND, "Sounds", ":/MO/gui/content/sound"),
        (Content.STRING, "Strings", ":/MO/gui/content/string"),
        (Content.LEVEL, "Levels", ":/MO/gui/content/bsa"),
    ]

    def getAllContents(self) -> list[mobase.ModDataContent.Content]:
        return [
            mobase.ModDataContent.Content(id, name, icon, *filter_only)
            for id, name, icon, *filter_only in self.GAMECONTENTS
        ]

    def walkContent(self, path: str, entry: mobase.FileTreeEntry):
        if entry.isFile():
            match entry.suffix().casefold():
                case "gif" | "jpg" | "jpeg" | "bmp" | "tga" | "png":
                    self.contents.append(Content.IMAGE)
                case "mo3":
                    self.contents.append(Content.MUSIC)
                case "xml":
                    self.contents.append(Content.SCRIPT)
                case "ogg":
                    self.contents.append(Content.SOUND)
                case "txt":
                    self.contents.append(Content.STRING)
                case "dat":
                    self.contents.append(Content.LEVEL)
                case _:
                    pass
        return mobase.IFileTree.WalkReturn.CONTINUE

    def getContentsFor(self, filetree: mobase.IFileTree) -> list[int]:
        self.contents: list[int] = []
        filetree.walk(self.walkContent, "/")
        return list(self.contents)


class ZumaModDataChecker(mobase.ModDataChecker):
    def __init__(self, organizer: mobase.IOrganizer):
        super().__init__()
        self.organizer: mobase.IOrganizer = organizer
        self.organizer.modList().onModInstalled(self.fixInstalledMod)
        self.needsNameFix = False

    def sanitizeFolderName(self, name: str) -> tuple[str, bool]:
        invalid_chars = '+&<>:"|?*\\/'
        for char in invalid_chars:
            name = name.replace(char, "")
        name = "".join(c for c in name if ord(c) >= 32)
        name = name.rstrip(". ")
        if not name:
            return "FOLDERNAME", True
        return name, False

    def moveOverwriteMerge(self, source: str, destination: str):
        if not os.path.exists(destination):
            shutil.move(source, destination)
            return
        if os.path.isfile(source):
            os.replace(source, destination)
            return
        for item in os.listdir(source):
            s_item = os.path.join(source, item)
            d_item = os.path.join(destination, item)
            self.moveOverwriteMerge(s_item, d_item)
        os.rmdir(source)

    def fixInstalledMod(self, mod: mobase.IModInterface):
        if not self.needsNameFix:
            return

        game_levels_path = str(
            getattr(self.organizer.managedGame(), "GameLevelsPath", "levels")
        )
        filetree: mobase.IFileTree = mod.fileTree()
        placeholder_path = f"{game_levels_path}/FOLDERNAME"

        if not filetree.exists(placeholder_path, mobase.IFileTree.DIRECTORY):
            return

        modname = self.sanitizeFolderName(mod.name())[0]
        path = mod.absolutePath()
        old_path = os.path.join(path, placeholder_path)
        new_path = os.path.join(path, game_levels_path, modname)
        self.moveOverwriteMerge(old_path, new_path)
        self.needsNameFix = False

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        valid_folders = {
            "images",
            "levels",
            "music",
            "sounds",
            "fonts",
            "properties",
            "userdata",
        }

        for e in filetree:
            if e.isDir() and e.name().casefold() in valid_folders:
                return mobase.ModDataChecker.VALID
            if e.isFile() and e.suffix().casefold() == "exe":
                return mobase.ModDataChecker.VALID

        return mobase.ModDataChecker.FIXABLE

    def fileExistsInNextSubDir(self, filetree: mobase.IFileTree, name: str) -> bool:
        for branch in filetree:
            if isinstance(branch, mobase.IFileTree):
                for e in branch:
                    if e.name() == name:
                        return True
        return False

    def allMoveTo(self, filetree: mobase.IFileTree, toMoveTo: str) -> bool:
        entriesToMove: list[mobase.FileTreeEntry] = []
        for e in filetree:
            entriesToMove.append(e)
        for e in entriesToMove:
            filetree.move(e, toMoveTo, mobase.IFileTree.MERGE)
        return bool(entriesToMove)

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree | None:
        self.needsNameFix = False
        game_levels_path: str = str(
            getattr(self.organizer.managedGame(), "GameLevelsPath", "levels")
        )
        valid_folders = {
            "images",
            "levels",
            "music",
            "sounds",
            "fonts",
            "properties",
            "userdata",
        }
        entriesToMove: list[mobase.FileTreeEntry] = []

        if filetree.exists("map.txt", mobase.IFileTree.FILE):
            if self.allMoveTo(filetree, game_levels_path + "/FOLDERNAME/"):
                self.needsNameFix = True
        elif self.fileExistsInNextSubDir(filetree, "map.txt"):
            filetree.move(filetree[0], game_levels_path, mobase.IFileTree.MERGE)
        else:
            moveonce = False
            for branch in filetree:
                if isinstance(branch, mobase.IFileTree):
                    for entry in branch:
                        if entry.name().casefold() in valid_folders:
                            moveonce = True
            if moveonce:
                for branch in filetree:
                    if isinstance(branch, mobase.IFileTree):
                        for entry in branch:
                            entriesToMove.append(entry)

        for e in entriesToMove:
            filetree.move(e, "", mobase.IFileTree.MERGE)

        for branch in list(filetree):
            if isinstance(branch, mobase.IFileTree) and len(branch) == 0:
                filetree.remove(branch)

        return filetree


PROGRAM_DATA = os.getenv("ProgramData", "")


class ZumaGame(BasicGame, mobase.IPluginFileMapper):
    Name = "Zuma Deluxe Support Plugin"
    Author = "ModWorkshop"
    CategorySource = "modworkshop"
    Version = "1"
    GameName = "Zuma Deluxe"
    GameShortName = "zuma"
    GameSteamId = 3330
    GameBinary = "Zuma.exe"
    GameDataPath = "%GAME_PATH%"
    GameLevelsPath = "levels"
    GameLevelsXml = "levels/levels.xml"
    ProfileLevelsXml = "levels.xml"
    GameDocumentsDirectory = os.path.join(PROGRAM_DATA, "Steam", "Zuma", "userdata")
    GameSaveExtension = "sav"

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self.dataChecker = ZumaModDataChecker(organizer)
        self._register_feature(self.dataChecker)
        self._register_feature(ZumaModDataContent())
        self._register_feature(BasicGameSaveGameInfo())
        organizer.modList().onModStateChanged(self.updateLevels)
        organizer.modList().onModMoved(lambda name, old, new: self.rebuildLevels())
        organizer.modList().onModRemoved(lambda name: self.rebuildLevels())
        return True

    def normalizeZumaXmlText(self, text: str) -> str:
        # The shipped file is XML-like rather than strict XML. Normalize only the
        # profile copy we generate: quote unquoted values and keep the last value
        # for duplicate attributes, matching the waythe game seems to work
        text = re.sub(
            r'(\s[A-Za-z_:][\w:.-]*)=([^"\'\s>/][^\s>/]*)',
            r'\1="\2"',
            text,
        )

        tag_pattern = re.compile(
            r"<(?![!?/])([A-Za-z_][\w:.-]*)([^<>]*?)(/?)>", re.DOTALL
        )
        attr_pattern = re.compile(r'([A-Za-z_:][\w:.-]*)\s*=\s*"([^"]*)"')

        def normalize_tag(match: re.Match[str]) -> str:
            tag_name = match.group(1)
            attr_text = match.group(2)
            self_closing = match.group(3)

            attrs: dict[str, str] = {}
            order: list[str] = []
            for attr_match in attr_pattern.finditer(attr_text):
                key = attr_match.group(1)
                value = attr_match.group(2)
                if key in attrs:
                    order.remove(key)
                attrs[key] = value
                order.append(key)

            if not attrs:
                return match.group(0)

            attrs_text = " ".join(f'{key}="{attrs[key]}"' for key in order)
            return f"<{tag_name} {attrs_text}{' /' if self_closing else ''}>"

        return tag_pattern.sub(normalize_tag, text)

    def readTextFile(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()

    def writeTextFile(self, path: str, content: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)

    def attrValue(self, tag: str, attr: str) -> str | None:
        match = re.search(rf'\b{re.escape(attr)}="([^"]*)"', tag)
        if match:
            return match.group(1)
        return None

    def commaValues(self, value: str) -> list[str]:
        return [part.strip() for part in value.split(",") if part.strip()]

    def replaceCommaAttribute(
        self, content: str, attr: str, values_to_prepend: list[str]
    ) -> str:
        if not values_to_prepend:
            return content

        pattern = re.compile(rf'({re.escape(attr)}\s*=\s*")([^"]*)(")')
        match = pattern.search(content)
        if not match:
            return content

        existing = self.commaValues(match.group(2))
        new_values = [value for value in values_to_prepend if value not in existing]
        if not new_values:
            return content

        combined = new_values + existing
        replacement = match.group(1) + ",".join(combined) + match.group(3)
        return content[: match.start()] + replacement + content[match.end() :]

    def insertBeforeFirstTag(
        self, content: str, tag_name: str, insert_text: str
    ) -> str:
        if not insert_text.strip():
            return content

        match = re.search(rf"\n\s*<{tag_name}\b", content)
        if match:
            return (
                content[: match.start()]
                + "\n\n"
                + insert_text.strip()
                + content[match.start() :]
            )

        closing_match = re.search(r"\n\s*</Levels>", content)
        if closing_match:
            return (
                content[: closing_match.start()]
                + "\n\n"
                + insert_text.strip()
                + content[closing_match.start() :]
            )

        return content.rstrip() + "\n\n" + insert_text.strip() + "\n"

    def mergeMapTextIntoLevels(self, levels_content: str, map_content: str) -> str:
        map_content = self.normalizeZumaXmlText(map_content)

        graphics_tags = re.findall(r"<Graphics\b.*?</Graphics>", map_content, re.DOTALL)
        level_tags = re.findall(r"<Level\b[^>]*/>", map_content, re.DOTALL)

        existing_graphics_ids = set(
            re.findall(r"<Graphics\b[^>]*\bid=\"([^\"]+)\"", levels_content)
        )
        existing_level_graphics = set(
            re.findall(r"<Level\b[^>]*\bgraphics=\"([^\"]+)\"", levels_content)
        )
        existing_stage1 = []
        stage1_match = re.search(r'stage1\s*=\s*"([^"]*)"', levels_content)
        if stage1_match:
            existing_stage1 = self.commaValues(stage1_match.group(1))

        graphics_to_insert: list[str] = []
        for tag in graphics_tags:
            graphics_id = self.attrValue(tag, "id")
            if graphics_id and graphics_id not in existing_graphics_ids:
                graphics_to_insert.append(tag.strip())
                existing_graphics_ids.add(graphics_id)

        levels_to_insert: list[str] = []
        stage_ids_to_add: list[str] = []
        for tag in level_tags:
            graphics_id = self.attrValue(tag, "graphics")
            if graphics_id and graphics_id not in existing_level_graphics:
                levels_to_insert.append(tag.strip())
                existing_level_graphics.add(graphics_id)
                if (
                    graphics_id not in existing_stage1
                    and graphics_id not in stage_ids_to_add
                ):
                    stage_ids_to_add.append(graphics_id)

        if not stage_ids_to_add:
            for tag in graphics_tags:
                graphics_id = self.attrValue(tag, "id")
                if (
                    graphics_id
                    and graphics_id not in existing_stage1
                    and graphics_id not in stage_ids_to_add
                ):
                    stage_ids_to_add.append(graphics_id)

        levels_content = self.insertBeforeFirstTag(
            levels_content, "Graphics", "\n\n".join(graphics_to_insert)
        )
        levels_content = self.insertBeforeFirstTag(
            levels_content, "Level", "\n".join(levels_to_insert)
        )

        # Custom maps are inserted into stage1 because the game loads stage1 as
        # soon as the user presses Start Game.
        levels_content = self.replaceCommaAttribute(
            levels_content, "stage1", stage_ids_to_add
        )
        levels_content = self.replaceCommaAttribute(
            levels_content, "diffi1", ["lvl42" for _ in stage_ids_to_add]
        )

        return levels_content

    def activeModsByPriority(self) -> list[tuple[str, mobase.IModInterface]]:
        mod_list = self._organizer.modList()
        active_mods: list[tuple[str, mobase.IModInterface]] = []

        for name in mod_list.allModsByProfilePriority():
            if mod_list.state(name) != mobase.ModState.ACTIVE:
                continue
            mod = mod_list.getMod(name)
            active_mods.append((name, mod))

        return active_mods

    def rebuildLevels(self) -> None:
        profile_levels_path = os.path.join(
            self._organizer.profilePath(), self.ProfileLevelsXml
        )
        game_levels_path = os.path.join(
            self.dataDirectory().absolutePath(), self.GameLevelsXml
        )

        if not os.path.exists(game_levels_path):
            return

        levels_content = self.readTextFile(game_levels_path)
        active_mods = self.activeModsByPriority()

        # A full levels.xml mod acts as a replacement base. If more than one is
        # active, the later one in profile priority order wins.
        for _name, mod in active_mods:
            tree = mod.fileTree()
            if tree.exists("levels/levels.xml", mobase.IFileTree.FILE):
                levels_xml_path = os.path.join(
                    mod.absolutePath(), "levels", "levels.xml"
                )
                if os.path.exists(levels_xml_path):
                    levels_content = self.readTextFile(levels_xml_path)

        levels_content = self.normalizeZumaXmlText(levels_content)

        for _name, mod in active_mods:
            tree = mod.fileTree()
            if tree.exists("levels/map.txt", mobase.IFileTree.FILE):
                map_txt_path = os.path.join(mod.absolutePath(), "levels", "map.txt")
                if os.path.exists(map_txt_path):
                    levels_content = self.mergeMapTextIntoLevels(
                        levels_content, self.readTextFile(map_txt_path)
                    )

        self.writeTextFile(profile_levels_path, levels_content)

    def updateLevels(self, mods: dict[str, mobase.ModState]):
        self.rebuildLevels()

    def executables(self):
        return [
            mobase.ExecutableInfo(
                "Zuma Deluxe",
                QFileInfo(self.gameDirectory().absoluteFilePath(self.binaryName())),
            ),
            mobase.ExecutableInfo(
                "Delta Patcher", QFileInfo(self.gameDirectory(), "DeltaPatcher.exe")
            ),
        ]

    @cached_property
    def baseDlls(self) -> set[str]:
        base_dir = Path(self.gameDirectory().absolutePath())
        return {str(f.relative_to(base_dir)) for f in base_dir.glob("*.dll")}

    def executableForcedLoads(self) -> list[mobase.ExecutableForcedLoadSetting]:
        try:
            efls = super().executableForcedLoads()
        except AttributeError:
            efls = []
        libs: set[str] = set()
        tree: mobase.IFileTree | mobase.FileTreeEntry | None = (
            self._organizer.virtualFileTree()
        )
        if type(tree) is not mobase.IFileTree:
            return efls
        for e in tree:
            relpath = e.pathFrom(tree)
            if relpath and e.hasSuffix("dll") and relpath not in self.baseDlls:
                libs.add(relpath)
        exes = self.executables()
        efls = efls + [
            mobase.ExecutableForcedLoadSetting(
                exe.binary().fileName(), lib
            ).withEnabled(True)
            for lib in libs
            for exe in exes
        ]
        return efls

    def initializeProfile(self, directory: QDir, settings: mobase.ProfileSetting):
        modsPath = self.dataDirectory().absolutePath()
        profile_levels_path = os.path.join(
            directory.absolutePath(), self.ProfileLevelsXml
        )
        game_levels_path = os.path.join(
            self.dataDirectory().absolutePath(), self.GameLevelsXml
        )
        if (
            not os.path.exists(profile_levels_path)
            or os.path.getsize(profile_levels_path) == 0
        ):
            if os.path.exists(game_levels_path):
                profile_levels_content = self.normalizeZumaXmlText(
                    self.readTextFile(game_levels_path)
                )
                self.writeTextFile(profile_levels_path, profile_levels_content)
        if not os.path.exists(modsPath):
            os.mkdir(modsPath)
        super().initializeProfile(directory, settings)

    def mappings(self) -> list[mobase.Mapping]:
        return [
            mobase.Mapping(
                os.path.join(self._organizer.profilePath(), self.ProfileLevelsXml),
                self.gameDirectory().absolutePath() + "/" + self.GameLevelsXml,
                False,
                False,
            ),
        ]
