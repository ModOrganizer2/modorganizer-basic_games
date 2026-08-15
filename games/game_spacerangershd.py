# Copyright (c) 2026 ringill
# SPDX-License-Identifier: MIT

"""MO2 game plugin for Space Rangers HD: A War Apart.

Subclasses ``BasicGame`` so the standard ``basic_games`` games loop registers it in
MO2's game list, but overrides ``mappings``/``dataDirectory`` and the SRHD sync
helpers because SRHD loads mods from a two-level ``Mods\\<Category>\\<Mod>`` layout
that does not fit ``BasicGame``'s "one subfolder = one mod" assumption.

Ownership model: MO2 owns the mod files. Native SRHD mods live in the MO2 mods
directory (one folder per mod, named ``<Category>__<Mod>`` — see ``paths.py``), so
the left mod list is populated natively by MO2's ``ModInfo::updateFromDisc``. The
game folder keeps only ``Mods\\ModCFG.txt``; base game files are untouched. The
plugin:

- delivers each MO2-enabled mod into the engine's nested ``Mods\\<Category>\\<Mod>``
  path via ``mappings()`` (usvfs VFS), and disables MO2's flat auto-map of mod
  contents onto the data root by returning an empty ``getModMappings()`` so no flat
  ``Mods\\<Mod>`` copies leak into the VFS alongside the nested destinations,
- syncs load order and enabled state between ``ModCFG.txt`` and the MO2 profile's
  ``modlist.txt`` for every profile,
- equalizes ``Priority`` by writing ``Priority=1`` to every MO2-enabled mod's
  ``ModuleInfo.txt`` **in the MO2 copy** (not the game folder) so the engine's
  load order matches what MO2 shows.

A standalone run without MO2 loads no mods (they have been moved into MO2) — a
documented tradeoff of the ownership model.
"""

from __future__ import annotations

import struct
import zlib
from enum import IntEnum, auto
from pathlib import Path

from PyQt6.QtCore import QDir, QStandardPaths
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QMessageBox, QWidget

import mobase

from ..basic_features.basic_save_game_info import BasicGameSaveGameInfo
from ..basic_game import BasicGame
from .spacerangershd.contracts import (
    IssueKind,
    ModIssue,
    apply_contract_meta,
    evaluate_contracts,
)
from .spacerangershd.crash_log import crash_tail, run_span
from .spacerangershd.mod_data_checker import SpaceRangersHDModDataChecker
from .spacerangershd.modcfg import (
    PRIORITY_EQUALIZE_VALUE,
    read_current_mod,
    set_priority,
    write_current_mod,
)
from .spacerangershd.modlist import enabled_names, read_modlist, write_modlist
from .spacerangershd.paths import engine_path_to_mod_name, mod_name_to_engine_path

_GAME_NAME = "Space Rangers HD: A War Apart"
_GAME_SHORT_NAME = "spacerangersawarapart"
_GAME_BINARY = "Rangers.exe"
_GAME_DATA_DIR = "Mods"
_GAME_NEXUS_ID = 920
_GAME_STEAM_ID = 214730
# GOG Galaxy product ID (registry key HKLM\Software\Wow6432Node\GOG.com\Games):
_GAME_GOG_ID = 1207667113

# Upper bound (bytes) on the .sav text header to scan for the first zlib stream.
# The header holds short UTF-16LE strings (name, planet, etc.), so the screenshot
# block always begins well within this limit.
_SAV_HEADER_SCAN_LIMIT = 4096

# SRHD writes the last run's log to this literal filename (eight ``#`` characters)
# in the documents directory; previous runs are archived into ``Errors``.
_CRASH_LOG_NAME = "########.log"


class Problems(IntEnum):
    """Diagnosable problems reported via :class:`mobase.IPluginDiagnose`."""

    # The last run's log (########.log) contains an "Exception " line.
    LAST_RUN_CRASHED = auto()
    # An enabled native mod has an active Conflict= partner (also enabled).
    ACTIVE_CONFLICT = auto()
    # An enabled native mod's Dependence= target is disabled or not installed.
    UNMET_DEPENDENCE = auto()


def _sav_preview(save_path: Path) -> QImage | None:
    """Extract the embedded screenshot from an SRHD ``.sav`` file.

    An SRHD save is a short UTF-16LE text header followed by a sequence of
    zlib-compressed blocks; the first block is the save screenshot: a u32 width,
    u32 height, u32 stride (= width*3, 24bpp), then raw top-down RGB888 pixels.
    Returns a ``QImage`` for MO2's saves-tab preview, or ``None`` when the file
    isn't a readable SRHD save.
    """
    try:
        data = save_path.read_bytes()
    except OSError:
        return None
    if len(data) < 16:
        return None

    end = min(len(data) - 2, _SAV_HEADER_SCAN_LIMIT)
    for i in range(end):
        # Cheap zlib header test: CM=8 and (b0*256+b1) % 31 == 0.
        if (data[i] & 0x0F) != 8:
            continue
        if (data[i] * 256 + data[i + 1]) % 31 != 0:
            continue
        try:
            block = zlib.decompressobj().decompress(data[i:])
        except zlib.error:
            continue
        if len(block) < 12:
            continue
        width, height, stride = struct.unpack_from("<III", block)
        if stride != width * 3 or len(block) != 12 + width * height * 3:
            continue
        pixels = block[12:]
        # The screenshot block is already top-down RGB888 (stride == width*3), so
        # build the QImage directly; no channel swap or vertical flip needed.
        return QImage(pixels, width, height, width * 3, QImage.Format.Format_RGB888)
    return None


class SpaceRangersHDGame(BasicGame, mobase.IPluginFileMapper, mobase.IPluginDiagnose):
    # Class-level attributes required by BasicGameMappings; they feed both the
    # Steam/GOG game detection (BasicGame.detectGame) and the steamAPPId()/
    # gogAPPId() accessors inherited from BasicGame.
    Name = _GAME_NAME
    Author = "ringill"
    Version = "0.1.0"
    GameName = _GAME_NAME
    GameShortName = _GAME_SHORT_NAME
    GameBinary = _GAME_BINARY
    GameDataPath = _GAME_DATA_DIR
    GameSteamId = _GAME_STEAM_ID
    GameGogId = _GAME_GOG_ID
    GameSaveExtension = "sav"
    GameIniFiles = ["CFG.TXT"]

    _organizer: mobase.IOrganizer

    _parentWidget: QWidget
    """Set with `_organizer.onUserInterfaceInitialized()` — parent for dialogs."""

    _contract_issue_cache: dict[str, ModIssue]
    """Last computed contract violations, keyed by MO2 mod name (see ``contracts.py``)."""

    def __init__(self):
        super().__init__()
        mobase.IPluginFileMapper.__init__(self)
        mobase.IPluginDiagnose.__init__(self)
        self._contract_issue_cache = {}

    # --- IPlugin interface ---------------------------------------------------

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self._organizer = organizer
        self._register_feature(BasicGameSaveGameInfo(get_preview=_sav_preview))
        # Register a ModDataChecker so MO2's basic installer can validate an
        # archive as an SRHD mod data tree (anchored by ModuleInfo.txt). Without
        # one, gameFeature<ModDataChecker>() is null and the installer can't
        # determine the data folder — it wraps archives in the <mods> pseudo-root
        # and reports "Cannot check the content of <mods>".
        self._register_feature(SpaceRangersHDModDataChecker())
        organizer.onAboutToRun(lambda app: self.aboutToRun(app))
        organizer.onFinishedRun(self._onFinishedRun)
        organizer.onUserInterfaceInitialized(self._on_user_interface_initialized)
        # Recompute the Conflict=/Dependence= contract violations whenever a mod's
        # state (enabled/disabled) changes, so the Problems indicator stays instant
        # and the meta.ini colours/notes track the current toggle (ADR D12).
        organizer.modList().onModStateChanged(self._on_mod_state_changed)
        return True

    def description(self) -> str:
        return f"Adds support for {_GAME_NAME}"

    # --- IPluginGame interface ----------------------------------------------

    # detectGame(): inherited from BasicGame — uses the configured GameSteamId
    # to auto-locate a Steam installation of SRHD.

    def nexusGameID(self) -> int:
        return _GAME_NEXUS_ID

    def getSupportURL(self) -> str:
        return "https://www.nexusmods.com/games/spacerangersawarapart"

    def initializeProfile(
        self, directory: QDir, settings: mobase.ProfileSetting
    ) -> None:
        # Let BasicGame copy CFG.TXT into the profile when MO2 asks for it, so its
        # INI editor has a profile-local copy to work on.
        super().initializeProfile(directory, settings)
        # CurrentMod holds ``Category\\Mod`` engine paths; the MO2 modlist is keyed
        # by the MO2 folder name ``Category__Mod``, so convert each path first.
        current_paths = read_current_mod(self._modcfg_path())
        current_names = [engine_path_to_mod_name(path) for path in current_paths]
        entries = self._build_modlist_entries(current_names)
        write_modlist(Path(directory.absolutePath()) / "modlist.txt", entries)

    def documentsDirectory(self) -> QDir:
        # SRHD keeps its settings (CFG.TXT) in %Documents%\SpaceRangersHD, not in
        # the game install folder.
        docs = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        return QDir(f"{docs}/SpaceRangersHD")

    def savesDirectory(self) -> QDir:
        # Real saves live in %Documents%\SpaceRangersHD\Save (.sav files).
        docs = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        return QDir(f"{docs}/SpaceRangersHD/Save")

    def getModMappings(self) -> dict[str, list[str]]:
        # SRHD loads mods from nested ``Mods\<Category>\<Mod>`` paths, so the flat
        # auto-map MO2 applies by default (each mod folder onto the
        # dataDirectory()="Mods" root, see OrganizerCore::fileMapping) would leak
        # flat copies of mod contents into the data root in addition to the nested
        # destinations. Returning an empty map disables that auto-map entirely: the
        # VFS overlay is defined solely by mappings() below.
        return {}

    # --- IPluginFileMapper interface ----------------------------------------

    def mappings(self) -> list[mobase.Mapping]:
        data_dir = Path(self.dataDirectory().absolutePath())
        if not data_dir.is_dir():
            return []
        mappings: list[mobase.Mapping] = []
        modlist = self._organizer.modList()
        for name in modlist.allMods():
            if not modlist.state(name) & mobase.ModState.ACTIVE:
                continue
            engine_path = mod_name_to_engine_path(name)
            if engine_path is None:
                continue  # not a native SRHD mod — leave it out of the VFS overlay
            mod = modlist.getMod(name)
            if not mod:
                continue
            mod_path = Path(mod.absolutePath())
            if not mod_path.is_dir():
                continue
            # Each MO2 mod folder mirrors the data directory: its files live under
            # a ``<Category>\<Mod>`` subfolder (see paths.py), so the VFS overlay
            # maps just that subfolder onto the engine's ``Mods\<Category>\<Mod>``
            # destination. Mapping the subfolder (not the whole mod folder) keeps
            # MO2's own root metadata (meta.ini / generated ModuleInfo.txt) out of
            # the game's data directory.
            mappings.append(
                mobase.Mapping(
                    str(mod_path / engine_path),
                    str(data_dir / engine_path),
                    True,
                    True,
                )
            )
        return mappings

    # --- SRHD sync helpers ---------------------------------------------------

    def _modcfg_path(self) -> Path:
        return Path(self.dataDirectory().absolutePath()) / "ModCFG.txt"

    def _build_modlist_entries(self, current_mods: list[str]) -> list[tuple[str, bool]]:
        """Build ``(name, enabled)`` entries for a profile's ``modlist.txt``.

        Mods listed in ``CurrentMod`` are enabled, in engine order; any other native
        mod in the MO2 mods directory is appended as disabled so it shows up in MO2
        for toggling. Names are the MO2 folder names (``Category__Mod``); non-native
        mods are left for MO2 to manage itself.
        """
        entries: list[tuple[str, bool]] = [(name, True) for name in current_mods]
        known = set(current_mods)
        modlist = self._organizer.modList()
        for name in modlist.allMods():
            if mod_name_to_engine_path(name) is None:
                continue
            if name not in known:
                entries.append((name, False))
                known.add(name)
        return entries

    def aboutToRun(self, app: str) -> bool:
        # The active MO2 profile's modlist.txt is the source of truth for order and
        # enabled state; write it back into ModCFG.txt, then equalize Priority in the
        # MO2 copies so the engine's load order matches what MO2 shows. The ``if
        # order:`` guard keeps the game folder untouched when no mod is enabled.
        profile = self._organizer.profile()
        modlist_path = Path(profile.absolutePath()) / "modlist.txt"
        order = enabled_names(read_modlist(modlist_path))
        if order:
            # modlist.txt holds MO2 folder names; map them back to engine
            # ``Category\\Mod`` paths before writing CurrentMod. Names that don't
            # follow the convention are skipped (never written into CurrentMod).
            engine_order = [
                path
                for name in order
                if (path := mod_name_to_engine_path(name)) is not None
            ]
            write_current_mod(self._modcfg_path(), engine_order)
            self._set_enabled_priority(order)
        return True

    def _set_enabled_priority(self, enabled: list[str]) -> None:
        """Set every enabled mod's ``Priority`` to the equalization value.

        The engine sorts enabled mods ascending by ``Priority``; with every enabled
        mod equal the stable sort is a no-op, so ``CurrentMod`` order (driven by
        MO2 drag&drop) fully determines load order and the ``QueryWrongOrderFix``
        dialog never appears. The previous ``Priority`` value is not preserved.

        Targets the ``ModuleInfo.txt`` in each mod's **MO2 copy** (its folder in the
        MO2 mods directory), never the game folder.
        """
        enabled_set = set(enabled)
        modlist = self._organizer.modList()
        for name in enabled_set:
            mod = modlist.getMod(name)
            if not mod:
                continue
            mod_path = Path(mod.absolutePath())
            engine_path = mod_name_to_engine_path(name)
            if engine_path is None:
                continue  # not a native SRHD mod — nothing to equalize
            # The mod's own ModuleInfo.txt lives under the ``<Category>\<Mod>``
            # subfolder (the MO2 mod folder mirrors the data directory); writing
            # Priority there targets the copy the engine actually reads.
            set_priority(
                mod_path / engine_path / "ModuleInfo.txt", PRIORITY_EQUALIZE_VALUE
            )

    # --- Conflict=/Dependence= contract display (ADR D12) --------------------

    def _recompute_contracts(self) -> dict[str, ModIssue]:
        """Recompute contract violations and push them into ``meta.ini``.

        Reads each enabled native mod's ``Conflict=``/``Dependence=`` (via
        ``contracts.evaluate_contracts``), caches the result for the Problems
        dialog, and writes the legend ``color=``/``comments=`` into every enabled
        mod's root ``meta.ini``. MO2 re-reads ``meta.ini`` only via
        ``ModInfo::updateFromDisc`` (Refresh/launch), so colour+Notes appear there;
        the Problems indicator is refreshed separately with ``_invalidate()``.
        """
        issues = evaluate_contracts(self._organizer)
        self._contract_issue_cache = issues
        apply_contract_meta(self._organizer, issues)
        return issues

    def _on_mod_state_changed(self, mods: dict[str, mobase.ModState]) -> None:
        """Re-evaluate contracts after a mod toggle and refresh the Problems light.

        Subscribed in ``init()`` via ``organizer.modList().onModStateChanged``; the
        callback receives ``{name: new_state}`` for the mods that changed. The state
        change does not make MO2 re-read ``meta.ini``, so we re-write the colours
        here ourselves (task 12.6) and call ``_invalidate()`` so the Problems button
        reflects the new state instantly (task 12.4).
        """
        self._recompute_contracts()
        # IPluginDiagnose._invalidate() triggers the plugincontainer's
        # diagnosisUpdate() signal, which re-polls activeProblems() and updates the
        # Problems button (see plugincontainer.cpp, mainwindow.cpp). The binding
        # exposes this method with a leading underscore.
        self._invalidate()

    # --- Crash notification (########.log) ----------------------------------

    def _crash_log_path(self) -> Path:
        return Path(self.documentsDirectory().absolutePath()) / _CRASH_LOG_NAME

    def _last_run_crash_tail(self) -> str | None:
        """Return the last run's crash tail, or ``None`` when it didn't crash.

        Reads ``########.log`` in the documents directory and returns the text from
        the first ``Exception `` line to end of file. ``None`` means the log is
        missing/unreadable or clean (no ``Exception `` line).
        """
        return crash_tail(self._crash_log_path())

    def _last_run_span(self) -> str | None:
        """Return the last run's ``<start> - <end>`` local timestamps, or ``None``.

        ``start`` is the moment ``########.log`` was created (the launch), ``end``
        its last modification (the run's end), both in the client's local time.
        ``None`` when the file is missing or its times cannot be read.
        """
        span = run_span(self._crash_log_path())
        if span is None:
            return None
        return f"{span[0]} - {span[1]}"

    def _on_user_interface_initialized(self, window: QWidget) -> None:
        # Parent for the crash dialog; parenting the QMessageBox keeps the widget
        # alive and makes it window-modal (non-blocking to the calling code).
        self._parentWidget = window
        # The mod list is populated by the time the UI shows, so run one initial
        # recompute+apply: pre-existing conflicts get their meta.ini colours/notes
        # without waiting for a state toggle (ADR D12).
        self._recompute_contracts()

    def _onFinishedRun(self, path: str, exit_code: int) -> None:
        """Show a crash notification after the game process exits.

        Fires via ``organizer.onFinishedRun`` when a process MO2 launched ends.
        We only react to the game itself (by its binary name). The exit code is not
        a reliable crash signal for SRHD, so the decision is based on the last
        run's log instead: if it contains a line starting with ``Exception ``, show
        a dialog with the tail from that line to end of file. A clean or missing
        log means no notification (see task 10 / spec ``mo2-game-plugin``).

        The box is parented to the MO2 main window and shown non-blocking with
        ``show()``: the parent makes Qt own the C++ dialog, so it is not
        garbage-collected when this method returns (a parentless locally-created
        ``QMessageBox`` would be collected and never appear).
        """
        if not path.endswith(self.binaryName()):
            return  # not the SRHD game process
        tail = self._last_run_crash_tail()
        if not tail:
            return  # clean run, missing, or unreadable log
        box = QMessageBox(self._parentWidget)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Space Rangers HD: likely crash")
        box.setText(f"Errors were detected in the game log: {self._crash_log_path()}")
        span = self._last_run_span()
        span_line = f"Run: {span}" if span else "Run: (timestamps unavailable)"
        box.setDetailedText(
            f"{span_line}\n\nLog tail (from the first Exception):\n{tail}"
        )
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.show()

    # --- IPluginDiagnose interface ------------------------------------------

    def activeProblems(self) -> list[int]:
        # Surface a persistent Problems-button indicator whenever the last run
        # crashed, so MO2 shows it on startup (and periodically) without needing to
        # wait for the game to run again. On top of that, flag active conflicts and
        # unmet dependencies so the button also advertises the contract violations
        # this plugin surfaces (ADR D12). The issue cache is kept fresh by
        # ``_recompute_contracts`` (called on every state change and on UI init).
        problems: list[int] = []
        if self._last_run_crash_tail() is not None:
            problems.append(Problems.LAST_RUN_CRASHED)
        if any(
            issue.kind is IssueKind.CONFLICT
            for issue in self._contract_issue_cache.values()
        ):
            problems.append(Problems.ACTIVE_CONFLICT)
        if any(
            issue.kind is IssueKind.DEPENDENCE
            for issue in self._contract_issue_cache.values()
        ):
            problems.append(Problems.UNMET_DEPENDENCE)
        return problems

    def shortDescription(self, key: int) -> str:
        if key == Problems.LAST_RUN_CRASHED:
            return "Errors were noticed in the log of the last launch."
        if key == Problems.ACTIVE_CONFLICT:
            return "Active conflicts were detected between enabled mods."
        if key == Problems.UNMET_DEPENDENCE:
            return "Some enabled mods have unmet dependencies."
        return ""

    def fullDescription(self, key: int) -> str:
        if key == Problems.LAST_RUN_CRASHED:
            tail = self._last_run_crash_tail() or "(log unreadable)"
            span = self._last_run_span()
            span_line = f"Run: {span}" if span else "Run: (timestamps unavailable)"
            return (
                f"Errors were detected in the game log: {self._crash_log_path()}"
                f"\n{span_line}\n\n{tail}"
            )
        if key == Problems.ACTIVE_CONFLICT:
            kind = IssueKind.CONFLICT
        elif key == Problems.UNMET_DEPENDENCE:
            kind = IssueKind.DEPENDENCE
        else:
            return ""
        # One line per offending mod: "who conflicts with whom" / "what is missing".
        lines = [
            issue.detail
            for issue in self._contract_issue_cache.values()
            if issue.kind is kind
        ]
        return "\n".join(lines) if lines else ""

    def hasGuidedFix(self, key: int) -> bool:
        # A crash is diagnostic only — there is no automated fix MO2 could apply.
        return False

    def startGuidedFix(self, key: int) -> None:
        pass
