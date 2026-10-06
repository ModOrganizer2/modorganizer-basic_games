# Copyright (c) 2026 ringill
# SPDX-License-Identifier: MIT

"""Read/write of MO2 profile ``modlist.txt`` files.

MO2 records each mod on its own line, prefixed by ``+`` (enabled) or ``-``
(disabled), in top-to-bottom order matching the left pane. The bottom of the list
is the highest-priority (last loaded / overriding) mod.
"""

from __future__ import annotations

from pathlib import Path


def read_modlist(path: Path) -> list[tuple[str, bool]]:
    """Return ``(mod name, enabled)`` entries from a ``modlist.txt`` file, in order.

    Blank lines and separator comments are ignored.
    """
    entries: list[tuple[str, bool]] = []
    if not path.exists():
        return entries
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        enabled = stripped[0] == "+"
        name = stripped[1:]
        if name:
            entries.append((name, enabled))
    return entries


def write_modlist(path: Path, entries: list[tuple[str, bool]]) -> None:
    """Write the given entries to a ``modlist.txt`` file, in order."""
    lines = [f"{'+' if enabled else '-'}{name}" for name, enabled in entries]
    path.write_text("\n".join(lines), encoding="utf-8")


def enabled_names(entries: list[tuple[str, bool]]) -> list[str]:
    """Return the names of enabled mods, preserving their order."""
    return [name for name, enabled in entries if enabled]
