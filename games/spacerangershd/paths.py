# Copyright (c) 2026 ringill
# SPDX-License-Identifier: MIT

"""Mapping between the engine's ``Category\\Mod`` path and the MO2 mod identity.

This plugin owns native SRHD mods inside the MO2 mods directory, one folder per
mod. The engine still loads each mod from the nested ``Mods\\<Category>\\<Mod>``
path (see ``CurrentMod=`` in ``ModCFG.txt``), so every MO2 folder name must
encode which category and mod it maps to. This module is the single source of
truth for that convention, shared by the plugin (``mappings``/sync helpers) and
the one-time migration script.

Convention: the MO2 folder is named ``<Category>__<Mod>``. Encoding the category
as a prefix of a single folder name keeps it unambiguous and means the category
is never represented as its own mod entry in MO2's left pane.
"""

from __future__ import annotations

_SEPARATOR = "__"


def engine_path_to_mod_name(engine_path: str) -> str:
    """Encode an engine ``Category\\Mod`` path as an MO2 mod folder name.

    Accepts either backslash (``ModCFG.txt`` engine paths) or forward slash
    (``Path.as_posix()``) separators, so callers don't have to normalize first.
    """
    return engine_path.replace("\\", _SEPARATOR).replace("/", _SEPARATOR)


def mod_name_to_engine_path(mod_name: str) -> str | None:
    """Decode an MO2 mod folder name back to its engine ``Category\\Mod`` path.

    Returns ``None`` when the name does not follow the convention, so non-native
    mods (or a mod a user hand-added) are left alone rather than force-mapped.
    """
    parts = mod_name.split(_SEPARATOR, 1)
    if len(parts) != 2:
        return None
    category, mod = parts
    if not category or not mod:
        return None
    return f"{category}\\{mod}"
