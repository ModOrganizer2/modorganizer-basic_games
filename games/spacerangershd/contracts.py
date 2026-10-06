# Copyright (c) 2026 ringill
# SPDX-License-Identifier: MIT

"""Evaluate the engine's ``Conflict=``/``Dependence=`` contracts for MO2 display.

The engine reads these two fields from each mod's ``ModuleInfo.txt`` but MO2's
core knows nothing about them (there are no Conflict/Dependence columns and
``ModList::EColumn`` is a fixed compile-time enum). Only this plugin surfaces
them, via the three existing mechanisms described in ADR D12: a Problems-button
indicator (``IPluginDiagnose``), a row colour written as ``color=`` in
``meta.ini`` (rendered only in the Notes column), and a Notes reason written as
``comments=<Name> (<reason>)``.

This module holds the pure evaluation (registry + violation detection) and the
``meta.ini`` writer. It talks to MO2 only through the ``organizer`` object, so the
``_evaluate`` core is free of MO2 types and testable on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import mobase

from .modcfg import read_conflict_dependence, read_mod_display_name
from .paths import mod_name_to_engine_path

# MO2 stores these as ``color=`` in meta.ini (QColor.name() hex, see modinfo.cpp);
# it renders the colour only in the mod list's Notes column (modlist.cpp:375).
# Legend (ADR D12): red = active conflict, yellow = unmet dependence.
COLOR_CONFLICT = "#ff0000"
COLOR_DEPENDENCE = "#ffff00"

# Reason labels shown in the Notes column after the mod's own display name.
_CONFLICT_REASON = "conflicts with: "
_DEPENDENCE_REASON = "depends on: "


class IssueKind(Enum):
    CONFLICT = "conflict"
    DEPENDENCE = "dependence"


@dataclass(frozen=True)
class ModContract:
    """One native mod and the engine contracts its ``ModuleInfo.txt`` declares."""

    mo2_name: str
    engine_path: str  # ``Category\\Mod`` (identity convention, see paths.py)
    display_name: str  # ``Name=`` from ModuleInfo.txt (folder name as fallback)
    conflict: tuple[str, ...]  # referenced mod folder names
    dependence: tuple[str, ...]  # referenced mod folder names


@dataclass(frozen=True)
class ModIssue:
    """The legend colour + Notes text + detail for one enabled native mod."""

    mo2_name: str
    display_name: str
    kind: IssueKind
    color: str  # one of COLOR_CONFLICT / COLOR_DEPENDENCE
    note: str  # "<Name> (<reason>)" — written as ``comments=`` in meta.ini
    detail: str  # one-line sentence for the Problems dialog


def _qualified(contract: ModContract) -> str:
    """Return the disambiguated ``Name (<Category>\\<Mod>)`` form of a mod."""
    return f"{contract.display_name} ({contract.engine_path})"


def _collect(organizer: mobase.IOrganizer) -> dict[str, ModContract]:
    """Map every native mod's MO2 name to its engine contract.

    Only mods whose MO2 folder follows the ``<Category>__<Mod>`` convention are
    included; hand-added/non-native mods are left out, mirroring the VFS mapping.
    """
    modlist = organizer.modList()
    contracts: dict[str, ModContract] = {}
    for mo2_name in modlist.allMods():
        engine_path = mod_name_to_engine_path(mo2_name)
        if engine_path is None:
            continue
        mod = modlist.getMod(mo2_name)
        if not mod:
            continue
        module_info = Path(mod.absolutePath()) / engine_path / "ModuleInfo.txt"
        conflict, dependence = read_conflict_dependence(module_info)
        display_name = (
            read_mod_display_name(module_info) or engine_path.rsplit("\\", 1)[-1]
        )
        contracts[mo2_name] = ModContract(
            mo2_name=mo2_name,
            engine_path=engine_path,
            display_name=display_name,
            conflict=tuple(conflict),
            dependence=tuple(dependence),
        )
    return contracts


def _enabled_names(organizer: mobase.IOrganizer) -> set[str]:
    modlist = organizer.modList()
    return {
        name
        for name in modlist.allMods()
        if modlist.state(name) & mobase.ModState.ACTIVE
    }


def evaluate_contracts(organizer: mobase.IOrganizer) -> dict[str, ModIssue]:
    """Return the current violations, keyed by the offending mod's MO2 name.

    A reference in ``Conflict=``/``Dependence=`` is a mod folder name (the last
    component of the engine ``Category\\Mod`` path); it is resolved through the
    same identity mapping the rest of the plugin uses (see ``paths.py``). Only
    enabled mods are checked. A mod with an active conflict is red; otherwise an
    unmet dependence makes it yellow (red wins over yellow, ADR D12).
    """
    contracts = _collect(organizer)
    enabled = _enabled_names(organizer)
    return _evaluate(contracts, enabled)


def _evaluate(
    contracts: dict[str, ModContract], enabled: set[str]
) -> dict[str, ModIssue]:
    # Resolve a referenced folder name to the first native mod with that folder
    # name (the convention assumes folder names are unique within a game).
    by_folder: dict[str, ModContract] = {}
    for contract in contracts.values():
        folder = contract.engine_path.rsplit("\\", 1)[-1]
        by_folder.setdefault(folder, contract)

    issues: dict[str, ModIssue] = {}
    for mo2_name in enabled:
        contract = contracts.get(mo2_name)
        if contract is None:
            continue

        # Red first: an enabled partner in Conflict= makes this an active conflict.
        partners = [
            ref
            for ref in contract.conflict
            if (target := by_folder.get(ref)) is not None and target.mo2_name in enabled
        ]
        if partners:
            partner = by_folder[partners[0]]
            issues[mo2_name] = ModIssue(
                mo2_name=mo2_name,
                display_name=contract.display_name,
                kind=IssueKind.CONFLICT,
                color=COLOR_CONFLICT,
                note=(
                    f"{contract.display_name} "
                    f"({_CONFLICT_REASON}{partner.display_name})"
                ),
                detail=(
                    f"{contract.display_name} conflicts with enabled mod "
                    f"{_qualified(partner)}"
                ),
            )
            continue

        # Yellow: a Dependence= target that is disabled or not installed at all.
        missing = [
            ref
            for ref in contract.dependence
            if (target := by_folder.get(ref)) is None or target.mo2_name not in enabled
        ]
        if missing:
            target = by_folder.get(missing[0])
            target_label = target.display_name if target is not None else missing[0]
            detail_target = _qualified(target) if target is not None else missing[0]
            issues[mo2_name] = ModIssue(
                mo2_name=mo2_name,
                display_name=contract.display_name,
                kind=IssueKind.DEPENDENCE,
                color=COLOR_DEPENDENCE,
                note=(f"{contract.display_name} ({_DEPENDENCE_REASON}{target_label})"),
                detail=(
                    f"{contract.display_name} depends on {detail_target}, "
                    "which is disabled or not installed"
                ),
            )
    return issues


def apply_contract_meta(
    organizer: mobase.IOrganizer, issues: dict[str, ModIssue]
) -> None:
    """Write ``color=``/``comments=`` into each native mod's ``meta.ini``.

    For an enabled mod with an issue this sets the legend colour and the
    ``<Name> (<reason>)`` note; for a clean enabled mod it restores the plain
    display name and drops any stale ``color=``. A disabled mod that was coloured
    by an earlier recompute is cleaned the same way, so turning off the partner of
    a conflict clears the other mod's red too — the legend must track the current
    toggle everywhere, not just on the mod that was clicked. Disabled mods with no
    ``meta.ini`` are skipped (never created). The Notes column and row colour only
    refresh once MO2 re-reads ``meta.ini`` (``updateFromDisc``), which happens on
    Refresh/launch. Only files whose content actually changes are written, so a
    no-op never churns ``meta.ini``.
    """
    modlist = organizer.modList()
    contracts = _collect(organizer)
    enabled = _enabled_names(organizer)
    for mo2_name, contract in contracts.items():
        mod = modlist.getMod(mo2_name)
        if not mod:
            continue
        mod_dir = Path(mod.absolutePath())
        issue = issues.get(mo2_name)
        if issue is not None:
            write_mod_meta(mod_dir, issue.note, issue.color)
        elif mo2_name in enabled or (mod_dir / "meta.ini").exists():
            # Clean enabled mod, or a disabled mod with a stale legend: restore
            # the plain display name and drop the colour.
            write_mod_meta(mod_dir, contract.display_name, None)


def write_mod_meta(mod_dir: Path, comments: str, color: str | None) -> None:
    """Set ``comments=`` and ``color=`` in a mod's root ``meta.ini``.

    Only the ``comments`` and ``color`` keys of the ``[General]`` section are
    touched; every other key and section is preserved byte-for-byte (same targeted
    approach as the import tool's ``_write_mod_notes``). ``color=None`` removes
    the ``color`` key (so a mod that went clean no longer stays coloured). A
    missing file is created in MO2's format (opening with a ``[General]`` header,
    as MO2's own ``meta.ini`` does; QSettings otherwise stores ungrouped keys under
    ``[General]``). ``meta.ini`` is UTF-8, unlike the mod's UTF-16
    ``ModuleInfo.txt``. The file is only written when the resulting content
    differs, so repeated no-op recomputes never touch it.
    """
    path = mod_dir / "meta.ini"
    existing = path.read_text("utf-8") if path.exists() else ""
    lines = existing.splitlines()
    comments_line = f"comments={comments}"
    color_line = f"color={color}" if color is not None else None

    in_general = True  # keys before any section header belong to [General]
    general_header = -1  # index of a literal "[General]" line, if present
    comments_replaced = False
    color_seen = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_general = stripped == "[General]"
            if in_general:
                general_header = len(out)
            out.append(line)
            continue
        if in_general:
            if stripped.lower().startswith("comments="):
                out.append(comments_line)
                comments_replaced = True
                continue
            if stripped.lower().startswith("color="):
                color_seen = True
                if color_line is not None:
                    out.append(color_line)
                continue  # colour line dropped when color is None
        out.append(line)

    # Insert any keys that were not already present. They must land in the
    # [General] section: after a literal "[General]" header when one exists,
    # otherwise we prepend the header explicitly (MO2's own meta.ini always opens
    # with [General], and a leading run of ungrouped keys also belongs to it).
    missing: list[str] = []
    if not comments_replaced:
        missing.append(comments_line)
    if color_line is not None and not color_seen:
        missing.append(color_line)

    if missing:
        if general_header >= 0:
            idx = general_header + 1
        else:
            out.insert(0, "[General]")
            idx = 1
        for offset, key in enumerate(missing):
            out.insert(idx + offset, key)

    result = "\n".join(out) + "\n"
    if result != existing:
        path.write_text(result, "utf-8")
