# Copyright (c) 2026 ringill
# SPDX-License-Identifier: MIT

"""Archive installer that places Nexus SRHD mod archives into the MO2 mods directory.

A downloaded SRHD mod archive can wrap its content in any number of folders, so
the first job is to locate the mod's root: the engine anchors every mod on a
``ModuleInfo.txt`` at the mod folder's root, so we search the archive for that
file (top level first, then descending into nested folders). The mod's root is
the folder that directly contains ``ModuleInfo.txt``; everything it needs is
whatever sits alongside that file.

That root is then restructured into this plugin's identity convention (see
``paths.py``): the mod folder is named ``<SectionEng>__<Name>`` and its data
mirrors the engine's ``Mods\\<Category>\\<Mod>`` layout under a nested
``<SectionEng>\\<Name>`` subfolder. Because the MO2 mod folder thereby mirrors the
data directory, ``mappings()`` in ``game_spacerangershd.py`` picks the mod up
immediately with no further adjustment:

- ``<Name>`` is the folder that held ``ModuleInfo.txt`` in the archive; if the
  file sat at the archive root (no wrapping folder), ``Name=`` from the file is
  used instead. Both are sanitized (whitespace and Windows-invalid path
  characters removed) before becoming a folder name.
- ``<SectionEng>`` comes from the ``SectionEng=`` field in ``ModuleInfo.txt``.

An optional ``meta.ini`` found next to ``ModuleInfo.txt`` is not copied into the
mod. Instead the installer reads its values and merges them into the ``meta.ini``
MO2 forms when it records the nexus download, so download metadata and mod
authored metadata end up in one file:

- a key MO2's ``meta.ini`` lacks but the archive's has is added;
- a key both have, with a value in both, keeps MO2's value;
- a key MO2 has empty but the archive has populated is filled from the archive.

The merged ``meta.ini`` is placed at the mod folder root; every other file and
folder that sat beside ``ModuleInfo.txt`` (including ``ModuleInfo.txt`` itself)
goes under ``<SectionEng>\\<Name>\\``.

A broken archive (no ``ModuleInfo.txt``, no ``SectionEng=``, or an empty
``<Name>`` after sanitizing) fails the installation. MO2 calls
``isArchiveSupported`` on every installer for every archive install regardless of
the managed game, so this installer self-gates on the game being SRHD.
"""

from __future__ import annotations

from pathlib import Path

import mobase

from ..game_spacerangershd import SpaceRangersHDGame
from .modcfg import read_mod_display_name, read_mod_section

# Marker file that anchors a mod's root (see mod_data_checker.py).
_MODULE_INFO = "moduleinfo.txt"
# Optional mod-level metadata file whose values are merged into the MO2-formed
# meta.ini on install (never copied into the mod itself).
META_INI = "meta.ini"
# Characters forbidden in Windows paths (Path invalid + directory separators).
_WINDOWS_INVALID_CHARS = set('<>:"/\\|?*')


def _sanitize(value: str) -> str:
    """Strip whitespace and characters that cannot appear in a Windows path.

    Spaces are removed (per the archive naming convention) and the engine's
    ``Category\\Mod`` path forbids ``<>:"/\\|?*`` plus control characters. Returns
    an empty string when nothing usable remains, signalling a broken archive.
    """
    return "".join(
        ch
        for ch in value
        if not ch.isspace() and ch not in _WINDOWS_INVALID_CHARS and ord(ch) >= 32
    )


def _find_mod_root(
    tree: mobase.IFileTree,
) -> tuple[mobase.IFileTree, mobase.FileTreeEntry] | None:
    """Return ``(mod_root, module_info)`` of the first ``ModuleInfo.txt`` found.

    ``mod_root`` is the tree that directly contains ``module_info``. The search
    checks the top level first, then descends into nested folders in order
    (preorder depth-first), so the first match is the archive's shallowest mod
    root.
    """
    for entry in tree:
        if entry.isFile() and entry.name().casefold() == _MODULE_INFO:
            return tree, entry
        if isinstance(entry, mobase.IFileTree):
            found = _find_mod_root(entry)
            if found is not None:
                return found
    return None


def _find_meta_ini(mod_root: mobase.IFileTree) -> mobase.FileTreeEntry | None:
    """Return the ``meta.ini`` entry sitting beside ``ModuleInfo.txt``, if any."""
    for entry in mod_root:
        if entry.isFile() and entry.name().casefold() == META_INI:
            return entry
    return None


def _prune_wrappers(root: mobase.IFileTree, entry: mobase.IFileTree) -> None:
    """Detach ``entry`` and any now-empty ancestors up to (not including) ``root``.

    After the mod's files are moved out of a wrapper folder the folder is empty
    and would otherwise remain as a dangling container in the archive, so it is
    removed together with any ancestors that become empty as a result.
    """
    current: mobase.IFileTree | None = entry
    while current is not None and current is not root:
        parent = current.parent()
        if len(current) == 0:
            current.detach()
        else:
            break
        current = parent if isinstance(parent, mobase.IFileTree) else None


def read_meta_ini_text(path: Path) -> str:
    """Decode an SRHD ``meta.ini`` regardless of its on-disk encoding.

    SRHD meta files may be UTF-16 LE with a BOM, UTF-8, or single-byte
    windows-1251; try each in turn and return the first that decodes cleanly.
    """
    for encoding in ("utf-8-sig", "utf-16", "cp1251"):
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return ""


def parse_meta_ini(text: str) -> dict[str, str]:
    """Parse a flat ``key=value`` INI body into a dict (section headers skipped)."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("[") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if key:
            result[key] = value.strip()
    return result


def _read_meta_ini(
    manager: mobase.IInstallationManager, entry: mobase.FileTreeEntry
) -> dict[str, str]:
    """Read the ``key=value`` pairs from an archive ``meta.ini`` entry.

    The file is extracted to a temporary path that MO2 cleans up after the
    install; nothing is copied into the mod. Returns an empty dict when the file
    could not be read.
    """
    tmp = manager.extractFile(entry, silent=True)
    if not tmp:
        return {}
    return parse_meta_ini(read_meta_ini_text(Path(tmp)))


def _mo2_meta_ini(version: str, nexus_id: int) -> dict[str, str]:
    """The ``meta.ini`` keys MO2 has already formed for this nexus download.

    MO2 passes these to ``install()``; the rest of its ``meta.ini`` (gameName,
    repository, author, ...) is only added by MO2 after ``install()`` returns, so
    those are not part of the merge base here.
    """
    mo2: dict[str, str] = {}
    if version:
        mo2["version"] = version
    if nexus_id:
        mo2["modid"] = str(nexus_id)
    return mo2


def merge_meta_ini(mo2: dict[str, str], archive: dict[str, str]) -> dict[str, str]:
    """Merge archive ``meta.ini`` values into MO2's under the installer rules.

    ``mo2`` holds the keys MO2 has already formed (the nexus download's ``version``
    and ``modid``); ``archive`` holds the values read from the mod archive's
    ``meta.ini``. A key missing from ``mo2`` is added from ``archive``; a key both
    have keeps MO2's value unless MO2's is empty, in which case the archive's
    populated value is used. Empty archive values are ignored.
    """
    merged = dict(mo2)
    for key, value in archive.items():
        if value and (key not in merged or not merged[key]):
            merged[key] = value
    return merged


def _format_meta_ini(data: dict[str, str]) -> str:
    """Serialize a dict to a ``key=value`` INI body, one pair per CRLF line."""
    body = "\r\n".join(f"{key}={value}" for key, value in data.items())
    return body + ("\r\n" if body else "")


def _write_meta_ini(
    manager: mobase.IInstallationManager,
    tree: mobase.IFileTree,
    data: dict[str, str],
) -> None:
    """Create the merged ``meta.ini`` at the mod folder root via ``createFile``.

    A synthetic file entry (``addFile``) carries no archive index, so ``extract``
    ignores it; MO2 instead copies the temp file from ``createFile`` to the mod
    folder root (``target/meta.ini``) after extraction, where its own QSettings
    merge runs on top. ``data`` is written UTF-8 with a BOM so MO2's QSettings
    reads it back as UTF-8.
    """
    entry = tree.addFile(META_INI)
    tmp = manager.createFile(entry)
    if not tmp:
        return
    body = _format_meta_ini(data)
    # newline="" on write stops \n from being translated to os.linesep (CRLF on
    # Windows), which would corrupt the explicit \r\n into \r\r\n.
    with Path(tmp).open("w", encoding="utf-8-sig", newline="") as f:
        f.write(body)


def _restructure(
    tree: mobase.IFileTree,
    mod_root: mobase.IFileTree,
    name: str,
    section: str,
    meta_ini: mobase.FileTreeEntry | None,
) -> None:
    """Rearrange the archive so the mod folder holds ``<SectionEng>\\<Name>``.

    The mod folder (the archive root, which MO2 extracts to the mod folder) is
    left holding the merged ``meta.ini`` written by ``_write_meta_ini`` and a
    single ``<SectionEng>\\<Name>`` subfolder containing every file and folder
    that sat beside ``ModuleInfo.txt`` (including ``ModuleInfo.txt`` itself). The
    archive's own ``meta.ini`` (``meta_ini``) is detached rather than moved, so it
    is never copied into the mod; its values were already read for the merge. When
    the archive already uses the target layout, the only changes are dropping the
    archive ``meta.ini`` and adding the merged one.
    """
    data_dir = tree.addDirectory(f"{section}\\{name}")
    children = list(mod_root)
    for child in children:
        if child is data_dir:
            continue
        if child is meta_ini:
            # meta.ini is mod-level metadata: read (not copied) for the merge, so
            # detach it from the tree to keep it out of the extracted output.
            child.detach()
            continue
        if data_dir is not mod_root:
            # Move each remaining sibling of ModuleInfo.txt into the data folder.
            data_dir.move(child, "", mobase.IFileTree.InsertPolicy.MERGE)
    if data_dir is not mod_root:
        _prune_wrappers(tree, mod_root)


class SpaceRangersHDInstaller(mobase.IPluginInstallerSimple, mobase.IPlugin):
    """Install SRHD Nexus archives, restructuring them to this plugin's convention."""

    _organizer: mobase.IOrganizer

    def __init__(self):
        mobase.IPluginInstallerSimple.__init__(self)
        mobase.IPlugin.__init__(self)

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self._organizer = organizer
        return True

    def name(self) -> str:
        return "SRHD: Space Rangers HD archive installer"

    def author(self) -> str:
        return "ringill"

    def description(self) -> str:
        return (
            "Installs Space Rangers HD mod archives: finds the folder anchored by "
            "ModuleInfo.txt and restructures it into the "
            "<SectionEng>__<Name>\\<SectionEng>\\<Name> layout the plugin's VFS "
            "mapping expects, merging the archive's meta.ini values into MO2's."
        )

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo("0.1.0")

    def settings(self) -> list[mobase.PluginSetting]:
        return []

    def priority(self) -> int:
        # High so this installer wins over the generic installers for SRHD mods.
        return 1000

    def isManualInstaller(self) -> bool:
        return False

    def isArchiveSupported(self, tree: mobase.IFileTree) -> bool:
        # MO2 asks every installer for every archive, regardless of the managed
        # game, so gate on the game being SRHD as well as on the archive having a
        # ModuleInfo.txt.
        game = self._organizer.managedGame()
        if game.gameShortName() != SpaceRangersHDGame.GameShortName:
            return False
        return _find_mod_root(tree) is not None

    def install(
        self,
        name: mobase.GuessedString,
        tree: mobase.IFileTree,
        version: str,
        nexus_id: int,
    ) -> mobase.IFileTree | mobase.InstallResult:
        found = _find_mod_root(tree)
        if found is None:
            return mobase.InstallResult.FAILED
        mod_root, module_info = found

        # Read Name= / SectionEng= from the archive's ModuleInfo.txt. The file is
        # extracted to a temporary location that MO2 cleans up after the install.
        tmp = self._manager().extractFile(module_info, silent=True)
        if not tmp:
            return mobase.InstallResult.FAILED
        module_info_path = Path(tmp)
        display_name = read_mod_display_name(module_info_path)
        section = read_mod_section(module_info_path)

        # <Name> is the folder that held ModuleInfo.txt; if the file sat at the
        # archive root, fall back to the Name= value from the file.
        if mod_root is not tree:
            name_value = _sanitize(mod_root.name())
        else:
            name_value = _sanitize(display_name or "")
        section_value = _sanitize(section or "")
        if not name_value or not section_value:
            # Broken archive: without a valid <Name> or <SectionEng> the mod cannot
            # be mapped into the engine's Mods\<Category>\<Mod> layout.
            return mobase.InstallResult.FAILED

        name.update(f"{section_value}__{name_value}", mobase.GuessQuality.USER)

        meta_ini = _find_meta_ini(mod_root)
        if meta_ini is not None:
            # Read the archive's meta.ini (never copied), merge its values into the
            # meta.ini MO2 forms for this download, and write the result to the mod
            # folder root so MO2's own meta.ini merge runs on top of it.
            archive = _read_meta_ini(self._manager(), meta_ini)
            merged = merge_meta_ini(_mo2_meta_ini(version, nexus_id), archive)
            _restructure(tree, mod_root, name_value, section_value, meta_ini)
            _write_meta_ini(self._manager(), tree, merged)
        else:
            _restructure(tree, mod_root, name_value, section_value, None)
        return tree
