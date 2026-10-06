import re
from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import QFileInfo

import mobase

from ..basic_features import BasicModDataChecker, GlobPatterns
from ..basic_features.utils import is_directory
from ..basic_game import BasicGame


class ResidentEvilRequiemModDataChecker(BasicModDataChecker):
    """Mod data checker for Resident Evil Requiem (RE Engine).

    Mods are loaded at runtime by REFramework, which supports:

    - loose files under `natives/` (LooseFileLoader),
    - `.pak` mods placed in `pak_mods/` (IntegrityCheckBypass_LoadPakDirectory),
    - Lua scripts and native plugins under `reframework/`.

    Most mods on Nexus are packaged for Fluffy Mod Manager: the payload is
    wrapped in one or more folders (usually the mod name) next to Fluffy
    metadata (modinfo.ini, screenshots, readmes). Single-option archives are
    unwrapped automatically. Multi-option archives are ambiguous, so they fall
    through to the manual installer - but re-rooting to one option there gives
    a layout that is valid without further fixing, because the manual
    installer never applies `fix()`: Fluffy metadata is merely ignored, and
    `.pak` files are valid at the mod root because the whole mod is cleaned
    up on disk right after installation - see
    `ResidentEvilRequiemGame._fix_installed_mod()`, which covers manual and
    BAIN installs as well.
    """

    def __init__(self):
        super().__init__(
            GlobPatterns(
                valid=[
                    "natives",
                    "reframework",
                    "pak_mods",
                    # Pak storage of installed mods:
                    # ResidentEvilRequiemGame.mappings() maps its content
                    # into pak_mods/ with a load-order prefix.
                    "paks",
                    "dinput8.dll",
                    # Moved into paks/ after install, see
                    # ResidentEvilRequiemGame._fix_installed_mod().
                    "*.pak",
                ],
                # Fluffy Mod Manager metadata: inert, so keep it - this way
                # manually (re-)rooted mods are valid without any fixing.
                ignore=[
                    "modinfo.ini",
                    "screenshot.*",
                    "*.txt",
                    "*.md",
                    "*.jpg",
                    "*.jpeg",
                    "*.png",
                    "*.url",
                ],
                move={
                    # The archive was created from inside the natives folder.
                    "stm": "natives/",
                },
            )
        )

    def _wrapper_dir(self, filetree: mobase.IFileTree) -> mobase.IFileTree | None:
        """Find the single directory the mod payload is wrapped in.

        Fluffy mod archives usually wrap the payload in a folder named after
        the mod. Returns the only directory of `filetree` that is neither
        valid, movable nor ignorable, provided everything next to it is junk
        (ignorable). Returns None otherwise (e.g. for multi-option Fluffy
        packs with several wrapper candidates, which need a manual install).
        """
        rp = self._regex_patterns
        wrapper: mobase.IFileTree | None = None
        for entry in filetree:
            name = entry.name().casefold()
            if rp.ignore.match(name) or rp.delete.match(name):
                continue
            if rp.valid.match(name) or rp.move_match(name) is not None:
                # Meaningful content next to a potential wrapper: the base
                # checker already knows how to handle this level.
                return None
            if not is_directory(entry) or wrapper is not None:
                return None
            wrapper = entry
        return wrapper

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        status = super().dataLooksValid(filetree)
        if status is mobase.ModDataChecker.INVALID:
            wrapper = self._wrapper_dir(filetree)
            if wrapper is not None and (
                self.dataLooksValid(wrapper) is not mobase.ModDataChecker.INVALID
            ):
                status = mobase.ModDataChecker.FIXABLE
        return status

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        # Unwrap (possibly nested) Fluffy mod folders first.
        while (
            super().dataLooksValid(filetree) is mobase.ModDataChecker.INVALID
            and (wrapper := self._wrapper_dir(filetree)) is not None
        ):
            # Everything next to the wrapper is junk (see _wrapper_dir), and
            # the wrapper level disappears, so drop the junk with it.
            for entry in list(filetree):
                if entry.name() != wrapper.name():
                    entry.detach()
            filetree.merge(wrapper)
            wrapper.detach()
        return super().fix(filetree)


class ResidentEvilRequiemGame(
    BasicGame, mobase.IPluginFileMapper, mobase.IPluginDiagnose
):
    def __init__(self):
        BasicGame.__init__(self)
        mobase.IPluginFileMapper.__init__(self)
        mobase.IPluginDiagnose.__init__(self)

    def init(self, organizer: mobase.IOrganizer) -> bool:
        super().init(organizer)
        self._register_feature(ResidentEvilRequiemModDataChecker())
        organizer.modList().onModInstalled(self._fix_installed_mod)
        return True

    Name = "Resident Evil Requiem Support Plugin"
    Author = "HomerSimpleton Returns Again"
    Version = "1.0"

    GameName = "Resident Evil Requiem"
    GameShortName = "residentevilrequiem"
    GameNexusName = "residentevilrequiem"
    GameSteamId = 3764200

    GameBinary = "re9.exe"
    GameDataPath = "%GAME_PATH%"

    # Where installed mods store their paks. The folder overlays into the
    # game directory as an inert "paks" dir the game never reads - only the
    # numbered virtual copies created by mappings() are loaded. (Hiding the
    # folder with a .mohidden suffix breaks the explicit file mappings with
    # usvfs 0.5.6, so the inert leak is deliberate.)
    _PAK_STORAGE_DIR = "paks"

    _PAK_NUMBER_PREFIX = re.compile(r"^\d{4} - ", re.ASCII)

    # Fluffy Mod Manager metadata: only read by Fluffy itself, and colliding
    # between mods, so not worth keeping in the installed mod.
    _FLUFFY_METADATA_GLOBS = ("modinfo.ini", "screenshot.*")

    @staticmethod
    def _parse_modinfo(path: Path) -> dict[str, str]:
        """Parse a Fluffy Mod Manager modinfo.ini (plain key=value lines,
        no sections). Returns an empty dict if the file cannot be read."""
        info: dict[str, str] = {}
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            return info
        for line in text.splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() and value.strip():
                info.setdefault(key.strip().casefold(), value.strip())
        return info

    def _fix_installed_mod(self, mod: mobase.IModInterface) -> None:
        """Clean up a freshly installed mod on disk: salvage MO2 metadata
        from the Fluffy modinfo.ini, delete the Fluffy metadata files and
        collect .pak files (mod root and shipped pak_mods/) into the mod's
        pak storage folder, from where mappings() feeds them to
        REFramework. Files are never renamed after installation.

        The ModDataChecker cannot do this: neither the manual installer nor
        the BAIN installer apply `fix()`, and multi-option Fluffy packs have
        to go through one of those.
        """
        if self._organizer.managedGame() != self:
            return
        mod_path = Path(mod.absolutePath())
        # Fill MO2's metadata from modinfo.ini before it is deleted - but
        # never override what MO2 already knows (e.g. from a Nexus download).
        modinfo_path = mod_path / "modinfo.ini"
        if modinfo_path.is_file():
            modinfo = self._parse_modinfo(modinfo_path)
            version = modinfo.get("version")
            if version and not mod.version().isValid():
                mod.setVersion(mobase.VersionInfo(version))
            url = modinfo.get("homepage") or modinfo.get("website")
            if url and not mod.url():
                mod.setUrl(url)
        for pattern in self._FLUFFY_METADATA_GLOBS:
            for junk in mod_path.glob(pattern):
                if junk.is_file():
                    junk.unlink()
        # Collect the paks into the hidden storage folder.
        shipped_pak_mods = mod_path / "pak_mods"
        paks = [
            p
            for pak_dir in (mod_path, shipped_pak_mods)
            for p in pak_dir.glob("*.pak")
            if p.is_file()
        ]
        if paks:
            storage = mod_path / self._PAK_STORAGE_DIR
            storage.mkdir(exist_ok=True)
            for pak in paks:
                # Strip a leftover load-order prefix: load order is handled
                # by mappings() now.
                target = storage / self._PAK_NUMBER_PREFIX.sub("", pak.name)
                if not target.exists():
                    pak.rename(target)
        if shipped_pak_mods.is_dir() and not any(shipped_pak_mods.iterdir()):
            shipped_pak_mods.rmdir()

    # IPluginFileMapper: REFramework loads every *.pak found in pak_mods/ in
    # alphabetical order. The stored paks of all active mods are mapped into
    # pak_mods/ with a global sequence number prefix, so that the load order
    # follows MO2's mod order - the same scheme Fluffy Mod Manager uses with
    # its own number prefixes. The mapping is virtual and rebuilt on every
    # launch; nothing on disk changes. Within one mod, paks are ordered by
    # their case-insensitive file name, so renaming the files in the mod's
    # pak storage folder reorders them.

    def _active_mod_paths(self) -> Iterable[Path]:
        mods_parent_path = Path(self._organizer.modsPath())
        modlist = self._organizer.modList()
        for mod_name in modlist.allModsByProfilePriority():
            if modlist.state(mod_name) & mobase.ModState.ACTIVE:
                yield mods_parent_path / mod_name

    def mappings(self) -> list[mobase.Mapping]:
        pak_mods_dir = Path(self.gameDirectory().absolutePath()) / "pak_mods"
        # Without a directory link on pak_mods/, the virtual pak files below
        # are not enumerable - directory scans (like REFramework's) would
        # not see them (compare game_finalfantasy7remake.py). Anchor that
        # link with a dedicated, permanently empty plugin-data folder. No
        # createTarget: writes into the virtual pak_mods/ should still land
        # in overwrite via MO2's regular root mapping.
        anchor = (
            Path(self._organizer.pluginDataPath()) / "residentevilrequiem" / "pak_mods"
        )
        anchor.mkdir(parents=True, exist_ok=True)
        mappings: list[mobase.Mapping] = [
            mobase.Mapping(str(anchor), str(pak_mods_dir), True, False)
        ]
        number = 0
        for mod_path in self._active_mod_paths():
            storage = mod_path / self._PAK_STORAGE_DIR
            if not storage.is_dir():
                continue
            for pak in sorted(
                storage.glob("*.pak"), key=lambda pak: pak.name.casefold()
            ):
                if not pak.is_file():
                    continue
                number += 1
                mappings.append(
                    mobase.Mapping(
                        str(pak),
                        str(pak_mods_dir / f"{number:04d} - {pak.name}"),
                        False,
                    )
                )
        return mappings

    def _reframework_installed(self) -> bool:
        return QFileInfo(self.gameDirectory(), "dinput8.dll").exists()

    # IPluginDiagnose: mods only load through REFramework, so warn when it
    # is missing from the game directory.

    def activeProblems(self) -> list[int]:
        if self._organizer.managedGame() == self and not self._reframework_installed():
            return [self._PROBLEM_NO_REFRAMEWORK]
        return []

    _PROBLEM_NO_REFRAMEWORK = 0

    def shortDescription(self, key: int) -> str:
        return "REFramework is not installed in the game directory."

    def fullDescription(self, key: int) -> str:
        return (
            "REFramework provides the mod loaders this plugin relies on: loose files "
            "from natives/, .pak mods from pak_mods/ and scripts from reframework/. "
            "Without it, installed mods have no effect.\n\n"
            "Download REFramework from "
            "https://www.nexusmods.com/residentevilrequiem/mods/13 and extract it "
            "(dinput8.dll) directly into the game directory:\n"
            f"{self.gameDirectory().absolutePath()}\n\n"
            "Install it directly into the game directory rather than as a mod, so "
            "the loader DLL is always active regardless of the virtual file system."
        )

    def hasGuidedFix(self, key: int) -> bool:
        return False

    def startGuidedFix(self, key: int) -> None:
        pass
