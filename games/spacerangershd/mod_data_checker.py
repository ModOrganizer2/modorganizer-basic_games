# Copyright (c) 2026 ringill
# SPDX-License-Identifier: MIT

"""ModDataChecker for Space Rangers HD: A War Apart.

SRHD loads mods from ``Mods\\<Category>\\<Mod>``; every native mod folder is
anchored by a ``ModuleInfo.txt`` at its root (the engine reads it for the mod's
Name/Priority/Conflict/Dependence). The content around it is otherwise arbitrary
(``CFG\\``, ``DATA\\``, ``colored_assets.pkg``, ...), so a mod's data tree is
recognised by the presence of that file, not by enumerating folders.

Registering this feature (via ``SpaceRangersHDGame.init``) is what lets MO2's
basic installer decide an archive is a valid SRHD mod data tree. Without a
``ModDataChecker``, ``gameFeature<ModDataChecker>()`` returns null and the
installer cannot determine the data-folder layout — it wraps the archive in the
``<mods>`` pseudo-root and reports "Cannot check the content of <mods>".
"""

from __future__ import annotations

import mobase

# Marker file that anchors every SRHD mod's data tree.
_MODULE_INFO = "moduleinfo.txt"


def _is_data_tree(filetree: mobase.IFileTree) -> bool:
    """Return whether ``filetree`` is a valid SRHD mod data tree.

    A data tree is anchored by ``ModuleInfo.txt`` at its root; everything else
    (``CFG``, ``DATA``, loose files, ...) is allowed to vary between mods.
    """
    return any(
        entry.isFile() and entry.name().casefold() == _MODULE_INFO for entry in filetree
    )


def _contains_data_tree(filetree: mobase.IFileTree) -> bool:
    """Return whether ``filetree`` contains a data tree at any depth.

    Recurses through subfolders because an installed mod's data tree sits nested
    under the mod folder in the ``<SectionEng>\\<Name>`` layout; only the mod
    folder's root is handed to ``dataLooksValid``.
    """
    if _is_data_tree(filetree):
        return True
    return any(
        isinstance(entry, mobase.IFileTree) and _contains_data_tree(entry)
        for entry in filetree
    )


def _single_wrapper(filetree: mobase.IFileTree) -> mobase.IFileTree | None:
    """Return the only top-level directory of ``filetree``, or ``None``."""
    children = list(filetree)
    if len(children) != 1:
        return None
    only = children[0]
    if not isinstance(only, mobase.IFileTree):
        return None
    return only


class SpaceRangersHDModDataChecker(mobase.ModDataChecker):
    """Game feature that lets MO2's basic installer validate SRHD mod archives."""

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        # Direct data tree: ModuleInfo.txt sits at the archive root.
        if _is_data_tree(filetree):
            return mobase.ModDataChecker.VALID
        # A single top-level folder that is itself a data tree: the mod is wrapped
        # in its own folder (the common Nexus archive layout). ``fix()`` unwraps it.
        wrapper = _single_wrapper(filetree)
        if wrapper is not None and _is_data_tree(wrapper):
            return mobase.ModDataChecker.FIXABLE
        # Installed layout: the mod folder is ``<SectionEng>__<Name>`` and its data
        # tree sits nested under ``<SectionEng>\\<Name>`` (plus a top-level
        # ``meta.ini``), so ModuleInfo.txt is not at the root and the folder is not
        # a single wrapper. Recurse to recognise the tree as valid — otherwise every
        # installed mod would report "No valid game data" in MO2's Flags column.
        if _contains_data_tree(filetree):
            return mobase.ModDataChecker.VALID
        return mobase.ModDataChecker.INVALID

    def fix(self, filetree: mobase.IFileTree) -> mobase.IFileTree:
        # Unwrap a single folder that wraps a data tree: move its contents up into
        # the archive root, then drop the empty wrapper (same shape as
        # ``BasicModDataChecker``'s ``unfold`` handling).
        wrapper = _single_wrapper(filetree)
        if wrapper is not None and _is_data_tree(wrapper):
            filetree.merge(wrapper)
            wrapper.detach()
        return filetree
