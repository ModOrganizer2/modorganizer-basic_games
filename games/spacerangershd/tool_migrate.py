# Copyright (c) 2026 ringill
# SPDX-License-Identifier: MIT

"""MO2 tool-menu action that imports native SRHD mods into the mods directory.

Copy ownership model (see ``proposal.md`` / ``design.md``): the game keeps its
native mods in ``game\\Mods\\<Category>\\<Mod>`` and MO2 overlays them via VFS,
so the files stay untouched. The missing piece was a visible way to get those
native mods into MO2's left pane, which is populated from the instance mods
directory. This tool does exactly that: it copies each native mod into
``<instance>\\mods\\<Category>__<Mod>`` using the identity convention in
``paths.py``.

Copying (not moving) keeps the game folder intact. The game loads mods only per
``CurrentMod`` in ``ModCFG.txt``, which the plugin maps from MO2's ``modlist.txt``
on launch, so native mods are listed, enabled and ordered purely through MO2 even
though their source files remain in the game folder.

Re-running the tool is a re-sync: existing copies are overwritten from the current
game folder contents, and the active profile's ``modlist.txt`` is rewritten so its
enabled/disabled state and order match ``CurrentMod`` (this also bootstraps a
missing or empty ``modlist.txt``). A progress dialog keeps the user informed while
the copies run, since a large mod set can take a moment.

MO2 shows a mod's ``comments`` (from its root ``meta.ini``) in the mod list's Notes
column and in the hover tooltip, so the tool also writes the mod's own ``Name=``
(from its UTF-16 ``ModuleInfo.txt``) into ``meta.ini``. That surfaces the
human-readable name (e.g. ``Deutsch Modifikation``) in the list without renaming
the ``<Category>__<Mod>`` folder the plugin's VFS mapping depends on.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog

import mobase

from .installer import META_INI, merge_meta_ini, parse_meta_ini, read_meta_ini_text
from .modcfg import read_current_mod, read_mod_display_name
from .modlist import read_modlist, write_modlist
from .paths import engine_path_to_mod_name, mod_name_to_engine_path

_NAME = "SRHD: Import native mods"
_VERSION = mobase.VersionInfo("0.1.0")


def _native_mod_jobs(
    game_mods_root: Path, mo2_mods_dir: Path
) -> list[tuple[str, Path, Path, Path]]:
    """Return ``(label, source, mod_dir, nested)`` copy jobs for each native mod.

    Only directories under each ``game\\Mods\\<Category>`` are considered;
    ``ModCFG.txt`` and other loose files stay in place. The destination folder
    name follows the ``<Category>__<Mod>`` identity convention; the mod's files
    are nested under a ``<Category>\\<Mod>`` subfolder inside it, so the MO2 mod
    folder mirrors the data directory (see ``paths.py``).
    """
    jobs: list[tuple[str, Path, Path, Path]] = []
    if not game_mods_root.is_dir():
        return jobs
    for category in sorted(game_mods_root.iterdir()):
        if not category.is_dir():
            continue  # e.g. ModCFG.txt stays in place
        for source in sorted(category.iterdir()):
            if not source.is_dir():
                continue
            rel = source.relative_to(game_mods_root)  # Category\\Mod
            mod_dir = mo2_mods_dir / engine_path_to_mod_name(rel.as_posix())
            nested = mod_dir / rel
            # Label the copy with the mod's own ``Name=`` (from its ModuleInfo.txt),
            # falling back to the source folder name when the file is absent.
            label = read_mod_display_name(source / "ModuleInfo.txt") or source.name
            jobs.append((label, source, mod_dir, nested))
    return jobs


def copy_native_mods(
    game_mods_root: Path,
    mo2_mods_dir: Path,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> tuple[int, int]:
    """Copy each native mod into the MO2 mods directory, overwriting existing copies.

    Returns ``(created, updated)``. Each mod's files are copied into the nested
    ``<Category>\\<Mod>`` subfolder of its MO2 folder, so the folder mirrors the
    data directory; MO2-owned files such as ``meta.ini`` are preserved while
    matching source files overwrite the previous copy — re-running is a re-sync.
    The mod's own ``Name=`` is written into its root ``meta.ini`` ``comments`` and
    the source mod's ``meta.ini`` values (next to ``ModuleInfo.txt`` in the game
    folder) are merged into it, so MO2's Notes column shows the human-readable
    name and the Info window / update checks see ``version``. A source
    ``meta.ini`` is never left in the nested data folder.
    ``on_progress(index, total, label)`` is invoked before each copy when given.
    """
    jobs = _native_mod_jobs(game_mods_root, mo2_mods_dir)
    created = 0
    updated = 0
    total = len(jobs)
    for index, (_label, source, mod_dir, nested) in enumerate(jobs, start=1):
        if on_progress is not None:
            on_progress(index, total, _label)
        if nested.exists():
            updated += 1
        else:
            created += 1
        shutil.copytree(str(source), str(nested), dirs_exist_ok=True)
        # Merge the source mod's meta.ini (next to ModuleInfo.txt) into the mod
        # root and keep its values out of the data folder: meta.ini is mod-level
        # metadata that MO2 reads only from the mod folder root.
        _write_root_meta_ini(mod_dir, _label, source / META_INI)
        nested_meta = nested / META_INI
        if nested_meta.exists():
            nested_meta.unlink()
    return created, updated


def _general_keys(lines: list[str]) -> dict[str, str]:
    """Lowercased ``key -> value`` map of the ``[General]`` keys in ``lines``.

    Keys appearing before any section header belong to ``[General]`` too, so the
    walk starts in ``[General]`` and stops collecting once a later section is
    entered. This is the merge base for the source mod's ``meta.ini`` values.
    """
    general: dict[str, str] = {}
    in_general = True
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_general = stripped == "[General]"
            continue
        if not in_general:
            continue
        key, sep, value = stripped.partition("=")
        if sep and key.strip():
            general[key.strip().lower()] = value.strip()
    return general


def _source_meta_values(source_meta: Path) -> dict[str, str]:
    """The ``key=value`` pairs of the source mod's ``meta.ini``, or ``{}``.

    The file sits next to ``ModuleInfo.txt`` in the game folder and may be UTF-16,
    UTF-8, or windows-1251; ``read_meta_ini_text`` decodes each in turn. Keys are
    lowercased so the merge base stays uniform with ``_general_keys`` and a source
    ``Version=`` cannot collide with an existing ``version=`` into a duplicate.
    Absent files yield an empty dict so the merge is a no-op.
    """
    if not source_meta.exists():
        return {}
    raw = parse_meta_ini(read_meta_ini_text(source_meta))
    return {key.lower(): value for key, value in raw.items()}


def _write_root_meta_ini(mod_dir: Path, name: str, source_meta: Path) -> None:
    """Merge the source mod's ``meta.ini`` into the mod's root ``meta.ini``.

    MO2 reads a mod's metadata only from the mod folder root ``meta.ini``: it
    renders ``comments`` in the list's Notes column and tooltip, and parses
    ``version`` for the Info window and update checks. This writes the mod's own
    ``Name=`` into ``comments`` (so the human-readable name shows without renaming
    the ``<Category>__<Mod>`` folder the VFS mapping depends on) and merges the
    source ``meta.ini`` values (next to ``ModuleInfo.txt`` in the game folder)
    into the ``[General]`` section under the installer rules
    (``merge_meta_ini``): an existing non-empty value wins, the source fills a
    missing or empty key, and empty source values are ignored.

    Only ``[General]`` is touched; other sections and keys in an existing
    ``meta.ini`` are preserved verbatim. A missing file is created in MO2's format
    (ungrouped keys sit under ``[General]``). ``meta.ini`` is UTF-8, unlike the
    mod's UTF-16 ``ModuleInfo.txt``.
    """
    path = mod_dir / "meta.ini"
    lines = path.read_text("utf-8").splitlines() if path.exists() else []

    merged = merge_meta_ini(_general_keys(lines), _source_meta_values(source_meta))
    # comments is the mod's own Name=, always overwritten (shown in Notes).
    merged["comments"] = name

    existing = _general_keys(lines)
    new_keys = [key for key in merged if key not in existing]

    if not lines:
        body = "\n".join(["[General]"] + [f"{key}={merged[key]}" for key in merged])
        path.write_text(body + "\n", "utf-8")
        return

    # Update existing [General] key values in place, keeping each key's original
    # casing; leave other sections and keys untouched.
    out = list(lines)
    in_general = True
    for idx, line in enumerate(out):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_general = stripped == "[General]"
            continue
        key, sep, _ = stripped.partition("=")
        if in_general and sep and key.strip().lower() in merged:
            out[idx] = f"{key.strip()}={merged[key.strip().lower()]}"

    # Append merged keys that had no line, into [General] (before the first
    # section that follows it, or at the end of the file).
    if new_keys:
        block = [f"{key}={merged[key]}" for key in new_keys]
        insert_at = len(out)
        seen_general = False
        for idx, line in enumerate(out):
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                if stripped == "[General]":
                    seen_general = True
                elif seen_general or idx > 0:
                    insert_at = idx
                    break
        out[insert_at:insert_at] = block

    path.write_text("\n".join(out) + "\n", "utf-8")


def _native_mod_names(mo2_mods_dir: Path) -> list[str]:
    """Return MO2 folder names of native-mod copies present in the mods directory."""
    if not mo2_mods_dir.is_dir():
        return []
    return [
        entry.name
        for entry in sorted(mo2_mods_dir.iterdir())
        if entry.is_dir() and mod_name_to_engine_path(entry.name) is not None
    ]


def _sync_modlist(
    modlist_path: Path, current_names: list[str], mo2_mods_dir: Path
) -> None:
    """Rewrite ``modlist.txt`` so enabled state and order match ``CurrentMod``.

    Mods listed in ``CurrentMod`` are enabled, in engine order; every other native
    copy in the MO2 mods directory is appended as disabled so it shows up for
    toggling. Non-native mods are left for MO2 to manage. The file is only written
    when the content differs, so a no-op never clobbers MO2's own copy.
    """
    entries: list[tuple[str, bool]] = [(name, True) for name in current_names]
    known = set(current_names)
    for name in _native_mod_names(mo2_mods_dir):
        if name not in known:
            entries.append((name, False))
            known.add(name)
    if read_modlist(modlist_path) == entries:
        return
    write_modlist(modlist_path, entries)


class MigrateTool(mobase.IPluginTool, mobase.IPlugin):
    """Copies native SRHD mods from the game folder into the MO2 mods directory."""

    _organizer: mobase.IOrganizer

    def __init__(self):
        mobase.IPluginTool.__init__(self)
        mobase.IPlugin.__init__(self)

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self._organizer = organizer
        return True

    def name(self) -> str:
        return _NAME

    def displayName(self) -> str:
        return _NAME

    def author(self) -> str:
        return "ringill"

    def description(self) -> str:
        return (
            "Copy native Space Rangers HD mods from the game folder into the MO2 "
            "mods directory so they appear in the left pane, then sync the profile's "
            "modlist.txt to the enabled/disabled state in ModCFG.txt."
        )

    def version(self) -> mobase.VersionInfo:
        return _VERSION

    def settings(self) -> list[mobase.PluginSetting]:
        return []

    def tooltip(self) -> str:
        return self.description()

    def icon(self) -> QIcon:
        return QIcon()

    def display(self) -> None:
        game = self._organizer.managedGame()
        if not game:
            self._notify("No game is being managed.", QMessageBox.Icon.Warning)
            return
        game_mods_root = Path(game.gameDirectory().absolutePath()) / "Mods"
        mo2_mods_dir = Path(self._organizer.basePath()) / "mods"

        jobs = _native_mod_jobs(game_mods_root, mo2_mods_dir)
        if not jobs:
            self._notify(f"No native mods found in {game_mods_root}.")
            return

        progress = QProgressDialog(
            "Copying native SRHD mods…", "", 0, len(jobs), self._parentWidget()
        )
        progress.setWindowTitle(_NAME)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)
        progress.setCancelButton(None)
        progress.show()

        def _step(index: int, total: int, label: str) -> None:
            progress.setLabelText(f"Copying {label} ({index} of {total})…")
            progress.setValue(index)
            QApplication.processEvents()

        created, updated = copy_native_mods(
            game_mods_root, mo2_mods_dir, on_progress=_step
        )
        progress.close()

        profile = self._organizer.profile()
        modlist_path = Path(profile.absolutePath()) / "modlist.txt"
        current_names = [
            engine_path_to_mod_name(path)
            for path in read_current_mod(game_mods_root / "ModCFG.txt")
        ]
        _sync_modlist(modlist_path, current_names, mo2_mods_dir)

        text = (
            f"Done: {created} copied, {updated} updated (overwritten). "
            "Profile modlist.txt synced to enabled state from ModCFG.txt."
        )
        self._notify(text)

    def _notify(
        self, text: str, icon: QMessageBox.Icon = QMessageBox.Icon.Information
    ) -> None:
        box = QMessageBox(self._parentWidget())
        box.setWindowTitle(_NAME)
        box.setIcon(icon)
        box.setText(text)
        box.exec()
