# Copyright (c) 2026 ringill
# SPDX-License-Identifier: MIT

"""Parsing and writing of Space Rangers HD mod control files.

The engine reads the load order from ``Mods\\ModCFG.txt``: the ``CurrentMod=`` key
holds a comma separated, ordered list of enabled mod entries. Each mod's
``ModuleInfo.txt`` is UTF-16 LE with a BOM; ``ModCFG.txt`` is single-byte UTF-8,
both with CRLF line endings.
"""

from __future__ import annotations

from pathlib import Path

# Python's ``utf-16`` codec reads/writes the BOM automatically. ``ModCFG.txt`` is
# plain UTF-8 (not UTF-16), so the two files use different codecs.
_ENCODING = "utf-16"
_MODCFG_ENCODING = "utf-8"
_CURRENT_MOD_KEY = "CurrentMod="
_PRIORITY_KEY = "Priority="
_NAME_KEY = "Name="
_SECTIONENG_KEY = "SectionEng="
_CONFLICT_KEY = "Conflict="
_DEPENDENCE_KEY = "Dependence="

# Value written as ``Priority=`` into every MO2-enabled mod's ``ModuleInfo.txt``.
# Equalizing all enabled mods to one value makes the engine's stable sort a no-op,
# so load order follows ``CurrentMod`` exactly. Single place to tweak the
# equalization value (e.g. to ``-1`` during testing) — change it here and it applies
# everywhere (default argument + plugin call site).
PRIORITY_EQUALIZE_VALUE = 1


def _read_text(path: Path, encoding: str) -> str:
    """Read ``path`` with ``newline=""`` so CRLF/LF endings are preserved exactly.

    ``Path.read_text()`` only gained a ``newline`` parameter in Python 3.10, but
    MO2 2.5.x embeds an older interpreter, so use ``Path.open()`` (mirrors the
    builtin ``open()``, which supports ``newline`` in every supported version).
    """
    with path.open("r", encoding=encoding, newline="") as f:
        return f.read()


def _write_text(path: Path, data: str, encoding: str) -> None:
    """Write ``data`` with ``newline=""`` so preserved endings aren't translated.

    Same interpreter-compatibility reason as ``_read_text``: ``newline=""`` on
    write stops ``\n`` from being translated to ``os.linesep`` (CRLF on Windows),
    which would otherwise corrupt preserved CRLF endings into CRCRLF.
    """
    with path.open("w", encoding=encoding, newline="") as f:
        f.write(data)


def set_priority(module_info: Path, value: int = PRIORITY_EQUALIZE_VALUE) -> None:
    """Set the ``Priority=<value>`` field in a mod's ``ModuleInfo.txt``.

    The previous value is not preserved; the field is replaced if present. A mod
    without a ``Priority`` field is left untouched (minimal intervention).
    Equalizing ``Priority`` across every enabled mod is what hands full
    load-order control to ``CurrentMod``: the engine's stable sort becomes a
    no-op and the ``QueryWrongOrderFix`` dialog never appears.

    The rewrite is minimal: only the ``Priority`` field changes. Line endings
    (CRLF/LF) and a trailing newline on the last line are preserved as-is, and a
    file that already holds the target value — or has no ``Priority`` field at
    all — is left byte-for-byte untouched.
    """
    if not module_info.exists():
        return
    key = f"{_PRIORITY_KEY}{value}"
    # newline="" disables universal-newline translation so CRLF/LF endings are
    # preserved exactly; otherwise read_text would fold CRLF into LF and the
    # rewrite would silently normalise the file to LF.
    lines = _read_text(module_info, _ENCODING).splitlines(keepends=True)
    for index, line in enumerate(lines):
        content = line.rstrip("\r\n")
        if content.strip() == key:
            return  # already equalized — leave the file untouched
        if content.lstrip().startswith(_PRIORITY_KEY):
            lines[index] = key + line[len(content) :]
            break
    else:
        return  # no Priority field — minimal intervention: leave the file untouched
    # newline="" on write too: the default None translates ``\n`` to os.linesep
    # (CRLF on Windows), which would corrupt preserved CRLF endings into CRCRLF.
    _write_text(module_info, "".join(lines), _ENCODING)


def read_current_mod(path: Path) -> list[str]:
    """Return the ordered list of enabled mod names from a ``ModCFG.txt`` file.

    The order follows the file, which is the engine's load order (left to right
    meaning first loaded to last loaded / overriding).
    """
    if not path.exists():
        return []
    for line in path.read_text(encoding=_MODCFG_ENCODING).splitlines():
        stripped = line.strip()
        if stripped.startswith(_CURRENT_MOD_KEY):
            value = stripped[len(_CURRENT_MOD_KEY) :]
            return [entry.strip() for entry in value.split(",") if entry.strip()]
    return []


def write_current_mod(path: Path, mod_names: list[str]) -> None:
    """Write the given ordered mod list as ``CurrentMod=`` in ``ModCFG.txt``.

    Any existing ``CurrentMod=`` value is replaced; unrelated lines are preserved.
    Line endings (CRLF/LF) and a trailing newline are kept as-is, and a file that
    already holds the target value is left byte-for-byte untouched. Entries are
    joined with ``", "`` to match the format the game writes.
    """
    key_line = f"{_CURRENT_MOD_KEY}{', '.join(mod_names)}"
    if not path.exists():
        _write_text(path, key_line, _MODCFG_ENCODING)
        return

    lines = _read_text(path, _MODCFG_ENCODING).splitlines(keepends=True)
    for index, line in enumerate(lines):
        content = line.rstrip("\r\n")
        if content.strip() == key_line:
            return  # already current — leave the file untouched
        if content.strip().startswith(_CURRENT_MOD_KEY):
            lines[index] = key_line + line[len(content) :]
            break
    else:
        # No CurrentMod line: append one, reusing a line ending from the file
        # (default CRLF). If the last line has no newline, add one so the appended
        # entry starts on a fresh line.
        ending = "\r\n"
        for last in reversed(lines):
            if last.endswith("\r\n"):
                ending = "\r\n"
                break
            if last.endswith("\n"):
                ending = "\n"
                break
        if lines and not lines[-1].endswith(("\n", "\r\n")):
            lines[-1] += ending
        lines.append(key_line + ending)
    _write_text(path, "".join(lines), _MODCFG_ENCODING)


def read_mod_display_name(module_info: Path) -> str | None:
    """Return the ``Name=`` value from a mod's ``ModuleInfo.txt``.

    This is the mod's own display name (e.g. ``Deutsch Modifikation``). Returns
    ``None`` when the file is missing or has no ``Name=`` field, so callers can
    fall back to the folder name.
    """
    if not module_info.exists():
        return None
    for line in module_info.read_text(encoding=_ENCODING).splitlines():
        stripped = line.strip()
        if stripped.startswith(_NAME_KEY):
            return stripped[len(_NAME_KEY) :].strip()
    return None


def read_mod_section(module_info: Path) -> str | None:
    """Return the ``SectionEng=`` value from a mod's ``ModuleInfo.txt``.

    The engine groups mods into sections (e.g. ``AnotherMods``); ``SectionEng`` is
    the section's folder name, which this plugin uses as the ``<Category>`` half of
    the ``<Category>__<Mod>`` identity convention (see ``paths.py``). Returns
    ``None`` when the file is missing or has no ``SectionEng=`` field.
    """
    if not module_info.exists():
        return None
    for line in module_info.read_text(encoding=_ENCODING).splitlines():
        stripped = line.strip()
        if stripped.startswith(_SECTIONENG_KEY):
            return stripped[len(_SECTIONENG_KEY) :].strip()
    return None


def _read_mod_name_list(module_info: Path, key: str) -> list[str]:
    """Return the comma-separated mod list of a ``ModuleInfo.txt`` field.

    ``key`` is e.g. ``Conflict=`` or ``Dependence=``; each entry is a ``Mod``
    folder name. An empty or missing field yields an empty list, mirroring how
    the game treats such fields as "no contract".
    """
    if not module_info.exists():
        return []
    for line in module_info.read_text(encoding=_ENCODING).splitlines():
        stripped = line.strip()
        if stripped.startswith(key):
            value = stripped[len(key) :]
            return [entry.strip() for entry in value.split(",") if entry.strip()]
    return []


def read_conflict_dependence(module_info: Path) -> tuple[list[str], list[str]]:
    """Return the ``Conflict=`` and ``Dependence=`` mod lists of a mod.

    ``Conflict=`` lists mutually exclusive mods; ``Dependence=`` lists required
    mods. Each is a comma-separated list of ``Mod`` folder names (``Mod`` here is
    the two-level ``Category\\Mod`` or a bare ``Mod``, as the game writes them).
    Empty or missing fields yield empty lists.
    """
    return (
        _read_mod_name_list(module_info, _CONFLICT_KEY),
        _read_mod_name_list(module_info, _DEPENDENCE_KEY),
    )
