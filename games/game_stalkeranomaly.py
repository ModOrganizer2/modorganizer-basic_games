# -*- encoding: utf-8 -*-
from __future__ import annotations

import io
import struct
import lzokay
from pathlib import Path
from typing import List, Optional
from enum import IntEnum, IntFlag
from datetime import datetime

from PyQt5.QtCore import Qt, QDir, QFileInfo
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

import mobase

from ..basic_features.basic_save_game_info import (
    BasicGameSaveGame,
    BasicGameSaveGameInfo,
)
from ..basic_game import BasicGame


class StalkerAnomalyModDataChecker(mobase.ModDataChecker):
    _valid_folders: List[str] = [
        "appdata",
        "bin",
        "db",
        "gamedata",
    ]

    def __init__(self):
        super().__init__()

    def hasValidFolders(self, tree: mobase.IFileTree) -> bool:
        for e in tree:
            if e.isDir():
                if e.name().lower() in self._valid_folders:
                    return True

        return False

    def findLostData(self, tree: mobase.IFileTree) -> List[mobase.FileTreeEntry]:
        lost_db: List[mobase.FileTreeEntry] = []

        for e in tree:
            if e.isFile():
                if e.suffix().lower().startswith("db"):
                    lost_db.append(e)

        return lost_db

    def dataLooksValid(
        self, tree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        if self.hasValidFolders(tree):
            return mobase.ModDataChecker.VALID

        if self.findLostData(tree):
            return mobase.ModDataChecker.FIXABLE

        return mobase.ModDataChecker.INVALID

    def fix(self, tree: mobase.IFileTree) -> mobase.IFileTree:
        lost_db = self.findLostData(tree)
        if lost_db:
            rfolder = tree.addDirectory("db").addDirectory("mods")
            for r in lost_db:
                rfolder.insert(r, mobase.IFileTree.REPLACE)

        return tree


class Content(IntEnum):
    INTERFACE = 0
    TEXTURE = 1
    MESH = 2
    SCRIPT = 3
    SOUND = 4
    MCM = 5
    CONFIG = 6


class StalkerAnomalyModDataContent(mobase.ModDataContent):
    content: List[int] = []

    def __init__(self):
        super().__init__()

    def getAllContents(self) -> List[mobase.ModDataContent.Content]:
        return [
            mobase.ModDataContent.Content(
                Content.INTERFACE, "Interface", ":/MO/gui/content/interface"
            ),
            mobase.ModDataContent.Content(
                Content.TEXTURE, "Textures", ":/MO/gui/content/texture"
            ),
            mobase.ModDataContent.Content(
                Content.MESH, "Meshes", ":/MO/gui/content/mesh"
            ),
            mobase.ModDataContent.Content(
                Content.SCRIPT, "Scripts", ":/MO/gui/content/script"
            ),
            mobase.ModDataContent.Content(
                Content.SOUND, "Sounds", ":/MO/gui/content/sound"
            ),
            mobase.ModDataContent.Content(Content.MCM, "MCM", ":/MO/gui/content/menu"),
            mobase.ModDataContent.Content(
                Content.CONFIG, "Configs", ":/MO/gui/content/inifile"
            ),
        ]

    def walkContent(
        self, path: str, entry: mobase.FileTreeEntry
    ) -> mobase.IFileTree.WalkReturn:
        name = entry.name().lower()
        if entry.isFile():
            ext = entry.suffix().lower()
            if ext in ["dds", "thm"]:
                self.content.append(Content.TEXTURE)
                if path.startswith("gamedata/textures/ui"):
                    self.content.append(Content.INTERFACE)
            elif ext in ["omf", "ogf"]:
                self.content.append(Content.MESH)
            elif ext in ["script"]:
                self.content.append(Content.SCRIPT)
                if "_mcm" in name:
                    self.content.append(Content.MCM)
            elif ext in ["ogg"]:
                self.content.append(Content.SOUND)
            elif ext in ["ltx", "xml"]:
                self.content.append(Content.CONFIG)
                if path.startswith("gamedata/configs/ui"):
                    self.content.append(Content.INTERFACE)

        return mobase.IFileTree.WalkReturn.CONTINUE

    def getContentsFor(self, tree: mobase.IFileTree) -> List[int]:
        self.content = []
        tree.walk(self.walkContent, "/")
        return self.content


class IVec3:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self) -> str:
        return f"{self.x}, {self.y}, {self.z}"

    def set(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


class IVec4(IVec3):
    def __init__(self, x, y, z, w):
        super().__init__(x, y, z)
        self.w = w

    def __str__(self) -> str:
        return f"{self.x}, {self.y}, {self.z}, f{self.w}"

    def set(self, x, y, z, w):
        super().set(x, y, z)
        self.w = w


class IFlag:
    def __init__(self, flag: int):
        self._flag = flag

    def __str__(self) -> str:
        return str(self._flag)

    def assign(self, mask):
        self._flag = mask

    def has(self, mask) -> bool:
        return bool((self._flag & mask) == mask)

    def set(self, mask):
        self._flag |= mask

    def remove(self, mask):
        self._flag &= ~mask


class IReader:
    def __init__(self, buffer: bytes):
        self._buffer = buffer
        self._pos = 0

    def __len__(self) -> int:
        return len(self._buffer)

    def _read_(self, size: int):
        pos = min(len(self._buffer), self._pos + size)
        buffer = self._buffer[self._pos : pos]
        return (buffer, pos)

    def read(self, size: int = -1):
        if size < 0:
            size = len(self._buffer)
        if len(self._buffer) <= self._pos:
            return b""
        (buffer, pos) = self._read_(size)
        self._pos = pos
        return bytes(buffer)

    def peek(self, size: int = -1):
        if size < 0:
            size = len(self._buffer)
        if len(self._buffer) <= self._pos:
            return b""
        (buffer, pos) = self._read_(size)
        return bytes(buffer)

    def seek(self, pos: int, whence: int = io.SEEK_SET) -> int:
        if whence == 0:
            if pos < 0:
                raise ValueError(f"negative seek position {pos}")
            self._pos = pos
        elif whence == 1:
            self._pos = max(0, self._pos + pos)
        elif whence == 2:
            self._pos = max(0, len(self._buffer) + pos)
        else:
            raise ValueError("unsupported whence value")
        return self._pos

    def tell(self) -> int:
        return self._pos

    def elapsed(self) -> int:
        return len(self._buffer) - self._pos

    def eof(self) -> bool:
        return self.elapsed() <= 0

    def u8(self) -> int:
        return int(struct.unpack("<B", self.read(1))[0])

    def s8(self) -> int:
        return int(struct.unpack("<b", self.read(1))[0])

    def u16(self) -> int:
        return int(struct.unpack("<H", self.read(2))[0])

    def s16(self) -> int:
        return int(struct.unpack("<h", self.read(2))[0])

    def u32(self) -> int:
        return int(struct.unpack("<I", self.read(4))[0])

    def s32(self) -> int:
        return int(struct.unpack("<i", self.read(4))[0])

    def u64(self) -> int:
        return int(struct.unpack("<Q", self.read(8))[0])

    def s64(self) -> int:
        return int(struct.unpack("<q", self.read(8))[0])

    def bool(self) -> bool:
        return bool(struct.unpack("<?", self.read(1))[0])

    def float(self) -> float:
        return float(struct.unpack("<f", self.read(4))[0])

    def str(self) -> str:
        chars = bytearray()
        while True:
            c = self.read(1)
            if c == b"\x00":
                return str(chars, "utf-8")
            else:
                chars += c

    def fvec3(self) -> IVec3:
        (f1, f2, f3) = struct.unpack("<fff", self.read(12))
        return IVec3(f1, f2, f3)


class XRFlag(IntFlag):
    CHUNK_ALIFE = 0x0
    CHUNK_SPAWN = 0x1
    CHUNK_OBJECT = 0x2
    CHUNK_GAME_TIME = 0x5
    CHUNK_REGISTRY = 0x9

    SPAWN_VERSION = 1 << 5

    MSG_UPDATE = 0x0
    MSG_SPAWN = 0x1

    TRADER_INFINITE_AMMO = 0x1


class XRStream(IReader):
    def __init__(self, buffer: bytes):
        super().__init__(buffer)
        self.last_pos: int = 0

    def find_chunk(self, id: int) -> Optional[int]:
        dw_type = 0
        dw_size = 0
        success = False
        if self.last_pos != 0:
            self.seek(self.last_pos)
            dw_type = self.u32()
            dw_size = self.u32()
            if (dw_type & (~(1 << 31))) == id:
                success = True

        if not success:
            self.seek(0)
            while not self.eof():
                dw_type = self.u32()
                dw_size = self.u32()
                if (dw_type & (~(1 << 31))) == id:
                    success = True
                    break
                else:
                    self.seek(dw_size, io.SEEK_CUR)

            if not success:
                self.last_pos = 0
                return None

        if (self._pos + dw_size) < len(self._buffer):
            self.last_pos = self._pos + dw_size
        else:
            self.last_pos = 0

        return dw_size

    def open_chunk(self, id: int) -> Optional[XRStream]:
        size = self.find_chunk(id)
        if size and size != 0:
            data = self.read(size)
            return XRStream(data)
        return None


class XRAbstract:
    def __init__(self, name: str = ""):
        self._valid = False
        self.name = name
        self.name_replace = ""
        self.rp = 0xFE
        self.position = IVec3(0.0, 0.0, 0.0)
        self.angle = IVec3(0.0, 0.0, 0.0)
        self.respawn_time = 0
        self.id = 0xFFFF
        self.id_parent = 0xFFFF
        self.id_phantom = 0xFFFF
        self.flags = IFlag(0)
        self.version = 0
        self.game_type = IFlag(0)
        self.script_version = 0
        self.client_data: List[int] = []
        self.spawn_id = 0
        self.ini_str = ""

    def read_spawn(self, reader: IReader):
        spawn = reader.u16()
        if spawn != XRFlag.MSG_SPAWN:
            self._valid = False
            return
        self.name = reader.str()
        self.name2 = reader.str()
        reader.seek(1, io.SEEK_CUR)  # temp_gt
        self.rp = reader.u8()
        self.position = reader.fvec3()
        self.angle = reader.fvec3()
        self.respawn_time = reader.u16()
        self.id = reader.u16()
        self.id_parent = reader.u16()
        self.id_phantom = reader.u16()
        self.flags = IFlag(reader.u16())
        if self.flags.has(XRFlag.SPAWN_VERSION):
            self.version = reader.u16()
        if self.version == 0:
            reader._pos -= 2
            return
        if self.version > 120:
            self.game_type.set(reader.u16())
        if self.version > 69:
            self.script_version = reader.u16()
        if self.version > 70:
            cl_size = 0
            if self.version > 93:
                cl_size = reader.u16()
            else:
                cl_size = reader.u8()
            if cl_size > 0:
                for x in range(cl_size):
                    data = reader.u8()
                    self.client_data.append(data)
        if self.version > 79:
            self.spawn_id = reader.u16()
        self._valid = True

    def __bool__(self):
        return self._valid


class XRVisual:
    def __init__(self):
        self.visual_name = ""
        self.startup_animation = ""
        self.flags = IFlag(0)

    def read_visual(self, reader: IReader, version: int):
        self.visual_name = reader.str()
        self.flags = reader.u8()


class XRNETState:
    def __init__(self):
        self.position = IVec3(0.0, 0.0, 0.0)
        self.quaternion = IVec4(0.0, 0.0, 0.0, 0.0)
        self.enabled = False

    def read(self, reader: IReader, fmin: IVec3, fmax: IVec3):
        self.position = self.fvec_q8(reader, fmin, fmax)
        self.quaternion = self.fqt_q8(reader)
        self.enabled = bool(reader.u8())

    def clamp(self, val: float, low: float, high: float) -> float:
        if val < low:
            return low
        elif val > high:
            return high
        else:
            return val

    def fvec_q8(self, reader: IReader, fmin: IVec3, fmax: IVec3):
        vec = IVec3(0.0, 0.0, 0.0)
        vec.x = self.f_q8(reader, fmin.x, fmax.x)
        vec.y = self.f_q8(reader, fmin.y, fmax.y)
        vec.z = self.f_q8(reader, fmin.z, fmax.z)
        vec.x = self.clamp(vec.x, fmin.x, fmax.x)
        vec.y = self.clamp(vec.x, fmin.y, fmax.y)
        vec.z = self.clamp(vec.z, fmin.z, fmax.z)

    def fqt_q8(self, reader: IReader):
        vec = IVec4(0.0, 0.0, 0.0, 0.0)
        vec.x = self.f_q8(reader, -1.0, 1.0)
        vec.y = self.f_q8(reader, -1.0, 1.0)
        vec.z = self.f_q8(reader, -1.0, 1.0)
        vec.w = self.f_q8(reader, -1.0, 1.0)
        vec.x = self.clamp(vec.x, -1.0, 1.0)
        vec.y = self.clamp(vec.y, -1.0, 1.0)
        vec.z = self.clamp(vec.z, -1.0, 1.0)
        vec.w = self.clamp(vec.w, -1.0, 1.0)

    def f_q8(self, reader: IReader, fmin: float, fmax: float):
        return (float(reader.u8()) / 255.0) * (fmax - fmin) + fmin


class XRBoneData:
    def __init__(self):
        self.bones_mask = -1
        self.root_bone = 0
        self.min = IVec3(0.0, 0.0, 0.0)
        self.max = IVec3(0.0, 0.0, 0.0)
        self.bones = []

    def load(self, reader: IReader):
        self.bones_mask = reader.u64()
        self.root_bone = reader.u16()
        self.min = reader.fvec3()
        self.max = reader.fvec3()
        bones_count = reader.u16()
        for x in range(bones_count):
            bone = XRNETState()
            bone.read(reader, self.min, self.max)
            self.bones.append(bone)


class XRSkeleton:
    def __init__(self):
        self.source_id = -1
        self.saved_bones = XRBoneData()

    def read_state(self, reader: IReader):
        self.visual_animation = reader.str()
        flags = IFlag(reader.u8())
        self.source_id = reader.u16()
        if flags.has(4):
            self.saved_bones.load(reader)


class XRObject(XRAbstract):
    def __init__(self):
        super().__init__()
        self.graph_id = 0
        self.distance = 0.0
        self.direct_control = True
        self.node_id = 0
        self.story_id = -1
        self.spawn_story_id = -1

    def read_spawn(self, reader: IReader):
        super().read_spawn(reader)
        size = reader.u16()
        if size <= 2:
            self._valid = False
            return
        self.read_state(reader)

    def read_state(self, reader: IReader):
        self.graph_id = reader.u16()
        self.distance = reader.float()
        self.direct_control = bool(reader.u32())
        self.node_id = reader.u32()
        self.flags.set(reader.u32())
        self.ini_str = reader.str()
        self.story_id = reader.u32()
        self.spawn_story_id = reader.u32()

    def read_update(self, reader: IReader):
        update = reader.u16()
        if update != XRFlag.MSG_UPDATE:
            self._valid = False
            return


class XRDynamicObject(XRObject):
    def __init__(self):
        super().__init__()
        self.time_id = -1
        self.switch_counter = 0


class XRDynamicObjectVisual(XRDynamicObject, XRVisual):
    def __init__(self):
        XRDynamicObject.__init__(self)
        XRVisual.__init__(self)

    def read_state(self, reader: IReader):
        XRDynamicObject.read_state(self, reader)
        if self.version > 31:
            XRVisual.read_visual(self, reader, self.version)


class XRCreatureAbstract(XRDynamicObjectVisual):
    def __init__(self):
        super().__init__()
        self.team = 0
        self.squad = 0
        self.group = 0
        self.health = 1.0
        self.dynamic_out = []
        self.dynamic_in = []
        self.killer_id = -1
        self.death_time = 0

    def read_state(self, reader: IReader):
        super().read_state(reader)
        self.team = reader.u8()
        self.squad = reader.u8()
        self.group = reader.u8()
        self.health = reader.float() * 100

        for x in range(reader.u32()):
            _id = reader.u16()
            self.dynamic_out.append(_id)

        for x in range(reader.u32()):
            _id = reader.u16()
            self.dynamic_in.append(_id)

        self.killer_id = reader.u16()
        self.death_time = reader.u64()


class XRTraderAbstract:
    def __init__(self):
        self.money = 0
        self.max_item_mass = 0
        self.character_name = ""
        self.character_name_str = ""
        self.character_profile = ""
        self.specific_character = ""
        self.community_index = -1
        self.rank = -1  # -MAX_INT?
        self.reputation = -1  # -MAX_INT?
        self.dead_body_can_take = True
        self.dead_body_closed = False
        self.trader_flags = IFlag(0)
        self.trader_flags.remove(XRFlag.TRADER_INFINITE_AMMO)

    def read_state(self, reader: IReader):
        self.money = reader.u32()
        self.specific_character = reader.str()
        self.trader_flags.assign(reader.u32())
        self.character_profile = reader.str()
        self.community_index = reader.s32()
        self.rank = reader.s32()
        self.reputation = reader.s32()
        self.character_name_str = reader.str()
        self.dead_body_can_take = reader.u8() == 1
        self.dead_body_closed = reader.u8() == 1


class XRCreatureActor(XRCreatureAbstract, XRTraderAbstract, XRSkeleton):
    def __init__(self):
        XRCreatureAbstract.__init__(self)
        XRTraderAbstract.__init__(self)
        XRSkeleton.__init__(self)
        self.state = 0
        self.acceleration = IVec3(0.0, 0.0, 0.0)
        self.velocity = IVec3(0.0, 0.0, 0.0)
        self.radiation = 0.0
        self.weapon = 0
        self.num_items = 0
        self.holder_id = -1

    def read_spawn(self, reader: IReader):
        XRCreatureAbstract.read_spawn(self, reader)

    def read_state(self, reader: IReader):
        XRCreatureAbstract.read_state(self, reader)
        XRTraderAbstract.read_state(self, reader)
        XRSkeleton.read_state(self, reader)
        self.holder_id = reader.u16()

    def read_update(self, reader: IReader):
        XRCreatureAbstract.read_update(self, reader)
        # XRTraderAbstract.read_update(self, reader)
        self.state = reader.u16()
        # acceleration (r_sdir)
        reader.seek(2, io.SEEK_CUR)  # u16
        reader.seek(4, io.SEEK_CUR)  # float
        # velocity (r_sdir)
        reader.seek(2, io.SEEK_CUR)  # u16
        reader.seek(4, io.SEEK_CUR)  # float
        self.radiation = reader.float()
        self.weapon = reader.u8()
        self.num_items = reader.u16()


class StalkerAnomalySaveGame(BasicGameSaveGame):
    _factions = {
        0: "Loner",
        1: "Monster",
        2: "Trader",
        3: "Army",
        4: "Sin",
        5: "Bandit",
        6: "Duty",
        7: "Ecologist",
        8: "Freedom",
        9: "Mercenary",
        10: "Army",
        11: "Monolith",
        12: "Sin",
        13: "Loner",
        14: "Zombified",
        15: "Clear Sky",
        16: "UNISG",
        17: "Renegade",
        18: "Loner",
        19: "Bandit",
        20: "Duty",
        21: "Freedom",
        22: "Clear Sky",
        23: "Ecologist",
        24: "Mercenary",
        25: "Military",
        26: "Monolith",
        27: "Zombified",
        28: "Sin",
        29: "UNISG",
        30: "Renegade",
        31: "Participant",
    }

    _ranks = {
        1999: "Novice",
        3999: "Trainee",
        6999: "Experienced",
        9999: "Professional",
        14999: "Veteran",
        20999: "Expert",
        27999: "Master",
        "max": "Legend",
    }

    _reputation = {
        -2000: "Terrible",
        -1500: "Really Bad",
        -1000: "Very Bad",
        -500: "Bad",
        499: "Netural",
        999: "Good",
        1499: "Very Good",
        1999: "Really Good",
        "max": "Excellent",
    }

    def __init__(self, filepath: Path):
        super().__init__(filepath)
        self._filepath = filepath
        self.fetch()

    def readData(self, file) -> Optional[XRStream]:
        size = self._filepath.stat().st_size
        if size < 8:
            return None

        (start, version, source) = struct.unpack("@iii", file.read(12))
        if (start == -1) and (version >= 6):
            file.seek(12)
            data = file.read(size - 12)
            return XRStream(lzokay.decompress(data, source))

        return None

    def readObject(self, stream: XRStream):
        chunk = stream.open_chunk(XRFlag.CHUNK_OBJECT)
        if chunk:
            chunk.seek(4, io.SEEK_CUR)  # obj_count
            count_spawn = chunk.u16()
            spawn = IReader(chunk.read(count_spawn))
            actor = XRCreatureActor()
            actor.read_spawn(spawn)
            count_update = chunk.u16()
            update = IReader(chunk.read(count_update))
            actor.read_update(update)
            if actor:
                self._player = actor
        return None

    def getFaction(self) -> str:
        if self._player:
            player_faction = self._player.community_index
            for faction in self._factions:
                if player_faction == faction:
                    return self._factions[faction]
        return "Unknown"

    def getRank(self) -> str:
        if self._player:
            player_rank = self._player.rank
            for rank in self._ranks:
                if isinstance(rank, int):
                    if player_rank <= rank:
                        return self._ranks[rank]
        return self._ranks["max"]

    def getReputation(self) -> str:
        if self._player:
            player_rep = self._player.reputation
            for rep in self._reputation:
                if isinstance(rep, int):
                    if player_rep <= rep:
                        return self._reputation[rep]
        return self._reputation["max"]

    def fetch(self):
        save_clean = self._filepath.name.split(".scop", 1)[0]
        save_split = save_clean.split(" - ", 1)
        self.user = save_split[0]
        save_end = save_split[1].split("_", 1)
        if len(save_end) > 1:
            self.save_fmt = f"{save_end[0]} (#{save_end[1]})".title()
        else:
            self.save_fmt = f"{save_end[0]}".title()

        self.time = self._filepath.stat().st_mtime
        self.time_date = datetime.fromtimestamp(self.time)
        self.time_fmt = self.time_date.strftime("%I:%M %m/%d/%Y")
        with open(self._filepath, "rb") as file:
            stream = self.readData(file)
            if stream:
                self.readObject(stream)

    def getName(self) -> str:
        player = self._player
        if player:
            name = player.character_name_str
            time = self.time_fmt
            return f"{name}, {self.save_fmt} [{time}]"
        return ""

    def allFiles(self) -> List[str]:
        filepath = str(self._filepath)
        paths = [filepath]
        scoc = filepath.replace(".scop", ".scoc")
        if Path(scoc).exists():
            paths.append(scoc)
        dds = filepath.replace(".scop", ".dds")
        if Path(dds).exists():
            paths.append(dds)
        return paths


class StalkerAnomalySaveGameInfoWidget(mobase.ISaveGameInfoWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        layout = QVBoxLayout()
        self._labelSave = self.newLabel(layout)
        self._labelName = self.newLabel(layout)
        self._labelFaction = self.newLabel(layout)
        self._labelHealth = self.newLabel(layout)
        self._labelMoney = self.newLabel(layout)
        self._labelRank = self.newLabel(layout)
        self._labelReputation = self.newLabel(layout)
        self.setLayout(layout)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.black)
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        self.setWindowFlags(Qt.ToolTip | Qt.BypassGraphicsProxyWidget)  # type: ignore

    def newLabel(self, layout: QVBoxLayout) -> QLabel:
        label = QLabel()
        label.setAlignment(Qt.AlignLeft)
        palette = label.palette()
        palette.setColor(label.foregroundRole(), Qt.white)
        label.setPalette(palette)
        layout.addWidget(label)
        layout.addStretch()
        return label

    def setSave(self, save: mobase.ISaveGame):
        self.resize(240, 32)
        if not isinstance(save, StalkerAnomalySaveGame):
            return
        player = save._player
        if player:
            self._labelSave.setText(f"Save: {save.save_fmt}")
            self._labelName.setText(f"Name: {player.character_name_str}")
            faction = save.getFaction()
            self._labelFaction.setText(f"Faction: {faction}")
            self._labelHealth.setText(f"Health: {player.health:.2f}%")
            self._labelMoney.setText(f"Money: {player.money} RU")
            rank = player.rank
            rank_fmt = save.getRank()
            self._labelRank.setText(f"Rank: {rank_fmt} ({rank})")
            rep = player.reputation
            rep_fmt = save.getReputation()
            self._labelReputation.setText(f"Reputation: {rep_fmt} ({rep})")


class StalkerAnomalySaveGameInfo(BasicGameSaveGameInfo):
    def getSaveGameWidget(self, parent=None):
        return StalkerAnomalySaveGameInfoWidget(parent)


class StalkerAnomalyGame(BasicGame, mobase.IPluginFileMapper):
    Name = "STALKER Anomaly"
    Author = "Qudix"
    Version = "0.5.0"
    Description = "Adds support for STALKER Anomaly"

    GameName = "STALKER Anomaly"
    GameShortName = "stalkeranomaly"
    GameBinary = "AnomalyLauncher.exe"
    GameDataPath = ""

    GameSaveExtension = "scop"
    GameSavesDirectory = "%GAME_PATH%/appdata/savedgames"

    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)

    def init(self, organizer: mobase.IOrganizer):
        BasicGame.init(self, organizer)
        self._featureMap[mobase.ModDataChecker] = StalkerAnomalyModDataChecker()
        self._featureMap[mobase.ModDataContent] = StalkerAnomalyModDataContent()
        self._featureMap[mobase.SaveGameInfo] = StalkerAnomalySaveGameInfo()
        return True

    def executables(self):
        exes = []
        info = [
            ["Anomaly Launcher", "AnomalyLauncher.exe"],
            ["Anomaly (DX11-AVX)", "bin/AnomalyDX11AVX.exe"],
            ["Anomaly (DX11)", "bin/AnomalyDX11.exe"],
            ["Anomaly (DX10-AVX)", "bin/AnomalyDX10AVX.exe"],
            ["Anomaly (DX10)", "bin/AnomalyDX10.exe"],
            ["Anomaly (DX9-AVX)", "bin/AnomalyDX9AVX.exe"],
            ["Anomaly (DX9)", "bin/AnomalyDX9.exe"],
            ["Anomaly (DX8-AVX)", "bin/AnomalyDX8AVX.exe"],
            ["Anomaly (DX8)", "bin/AnomalyDX8.exe"],
        ]
        gamedir = self.gameDirectory()
        for inf in info:
            exes.append(mobase.ExecutableInfo(inf[0], QFileInfo(gamedir, inf[1])))
        return exes

    def listSaves(self, folder: QDir) -> List[mobase.ISaveGame]:
        ext = self._mappings.savegameExtension.get()
        return [
            StalkerAnomalySaveGame(path)
            for path in Path(folder.absolutePath()).glob(f"*.{ext}")
        ]

    def mappings(self) -> List[mobase.Mapping]:
        self.gameDirectory().mkdir("appdata")

        m = mobase.Mapping()
        m.createTarget = True
        m.isDirectory = True
        m.source = self.gameDirectory().filePath("appdata")
        m.destination = self.gameDirectory().filePath("appdata")
        return [m]
