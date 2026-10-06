# Copyright (c) 2026 ringill
# SPDX-License-Identifier: MIT

"""MO2 tool-menu action that assembles a Space Rangers HD mod bug-report archive.

The game's crash notification (see ``game_spacerangershd.py``) surfaces the last
run's crash, but a mod author still needs context to reproduce a bug: which mod
the user suspects, which save was involved, the game's own log, and any
screenshots of the problem. This tool opens a small form split into sections —
what happened, where it happened, how to reproduce, who the user suspects, plus
two attachment sections (user screenshots and automatically collected technical
files) — then packs everything into a ``.zip`` on "Save".

Nothing on the form is mandatory. The user may leave the mod and/or save unset
even though the form recommends them; skipped fields simply don't end up in the
archive. The archive always carries at least the game version from
``Rangers.exe`` (via the managed game's ``gameVersion()``, which calls
``mobase.getFileVersion``) and the full text of the last run's ``########.log``
(``read_log`` in ``crash_log.py``). The exact set of fields/files is expected to
grow after the first MVP.
"""

from __future__ import annotations

import os
import zipfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import mobase

from .crash_log import read_log, run_span
from .modcfg import read_mod_display_name
from .paths import mod_name_to_engine_path

_NAME = "SRHD: Report a mod bug"
_VERSION = mobase.VersionInfo("0.1.0")

# Placeholder first entry of each filterable combo is blank: an unset field is
# simply empty, and the value is omitted from the archive.
_NONE_MOD = ""
_NONE_SAVE = ""

_REPORT_FILENAME = "report.txt"

# Screenshots live wherever the user keeps them on disk (outside MO2); this filter
# is offered in the multi-select dialog. Technical files (log, modlist, ModCFG)
# may be any file on disk, so the technical section offers a broad filter.
_SCREENSHOT_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
_TECH_FILTER = "All files (*)"


def _combo_data(combo: QComboBox) -> object:
    """Return the ``itemData`` of the item matching the combo's current text.

    The ``data`` is the stable identity read back for the report and archive.
    ``None`` is returned when nothing valid is selected: the combo is empty, or
    the text does not exactly match one of the items.
    """
    text = combo.currentText().strip()
    if not text:
        return None
    for i in range(combo.count()):
        if combo.itemText(i) == text:
            return combo.itemData(i)
    return None


def _current_reporter(organizer: mobase.IOrganizer) -> str:
    """Best-effort default for the Reporter field.

    Prefer the Nexus username when MO2 is authenticated there, else the current
    Windows user from the environment, else empty. The returned string may be
    edited or cleared by the user on the form.
    """
    # ``getCurrentUsername`` is not declared in the mobase stubs, so reach it via
    # getattr and stay graceful if the runtime MO2 lacks the method entirely.
    username = getattr(organizer, "getCurrentUsername", None)
    if callable(username):
        try:
            name = username()
        except Exception:
            name = None
        if isinstance(name, str) and name.strip():
            return name.strip()
    for key in ("USERNAME", "USER"):
        name = os.environ.get(key, "").strip()
        if name:
            return name
    return ""


def _filename_slug(value: str) -> str:
    """Strip characters that are not allowed in a Windows file name."""
    for ch in ("<", ">", ":", '"', "/", "\\", "|", "?", "*"):
        value = value.replace(ch, "")
    return value.strip().strip(" .")


def _attachments_group(
    parent: QWidget,
    title: str,
    hint: str,
    file_filter: str,
    seed: list[Path],
    *,
    button_text: str = "Add files…",
) -> tuple[QGroupBox, Callable[[], list[Path]]]:
    """Build an editable file list section and return it with a path getter.

    The returned ``QGroupBox`` holds a multi-select ``QListWidget`` pre-populated
    with ``seed`` plus Add / Remove selected / Clear all buttons. The caller reads
    back the final list of paths (full path stored in ``UserRole``) via the getter.
    """
    group = QGroupBox(title, parent)
    layout = QVBoxLayout(group)
    hint_label = QLabel(hint, group)
    hint_label.setWordWrap(True)
    layout.addWidget(hint_label)

    listing = QListWidget(group)
    listing.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    listing.setMinimumHeight(72)
    for path in seed:
        item = QListWidgetItem(path.name)
        item.setData(Qt.ItemDataRole.UserRole, str(path))
        item.setToolTip(str(path))
        listing.addItem(item)

    add_button = QPushButton(button_text, group)
    remove_button = QPushButton("Remove selected", group)
    clear_button = QPushButton("Clear all", group)

    def _paths() -> list[Path]:
        result: list[Path] = []
        for i in range(listing.count()):
            item = listing.item(i)
            if item is not None:
                data = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(data, str):
                    result.append(Path(data))
        return result

    def _on_add() -> None:
        chosen, _filter = QFileDialog.getOpenFileNames(
            parent, title, str(Path.home()), file_filter
        )
        existing = set(_paths())
        for text in chosen:
            path = Path(text)
            if path in existing:
                continue
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            listing.addItem(item)
            existing.add(path)

    def _on_remove() -> None:
        for item in listing.selectedItems():
            listing.takeItem(listing.row(item))

    def _on_clear() -> None:
        listing.clear()

    add_button.clicked.connect(_on_add)  # type: ignore
    remove_button.clicked.connect(_on_remove)  # type: ignore
    clear_button.clicked.connect(_on_clear)  # type: ignore

    buttons = QHBoxLayout()
    buttons.addWidget(add_button)
    buttons.addWidget(remove_button)
    buttons.addWidget(clear_button)
    buttons.addStretch()
    layout.addLayout(buttons)
    layout.addWidget(listing)
    return group, _paths


def _filterable_combo(parent: QDialog, items: list[tuple[str, object]]) -> QComboBox:
    """Build an editable ``QComboBox`` with substring filtering over ``items``.

    Each ``items`` entry is ``(label, data)``; the data is the stable identity the
    tool reads back via ``currentData()``, decoupled from whatever the user typed.
    Editable + ``QCompleter`` with ``MatchContains`` (case-insensitive) lets the
    user type a few characters to filter a long mod/save list instead of scrolling
    it.
    """
    combo = QComboBox(parent)
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    combo.setMaxVisibleItems(15)
    for label, data in items:
        combo.addItem(label, data)
    completer = QCompleter(combo.model(), combo)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    combo.setCompleter(completer)
    return combo


class BugReportTool(mobase.IPluginTool, mobase.IPlugin):
    """Opens a mod bug-report form and packs the collected data into a ``.zip``."""

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
            "Assemble a Space Rangers HD mod bug-report archive: describe the "
            "problem, optionally pick a suspected mod and a save, and save a .zip "
            "with the game version, the last run's log, and any attached data."
        )

    def version(self) -> mobase.VersionInfo:
        return _VERSION

    def settings(self) -> list[mobase.PluginSetting]:
        return []

    def tooltip(self) -> str:
        return self.description()

    def icon(self) -> QIcon:
        return QIcon()

    # --- Form construction ------------------------------------------------

    def _enabled_mods(self, modlist: mobase.IModList) -> list[str]:
        """Return the MO2 names of all enabled mods, sorted alphabetically."""
        return sorted(
            name
            for name in modlist.allMods()
            if modlist.state(name) & mobase.ModState.ACTIVE
        )

    def _mod_label(self, modlist: mobase.IModList, name: str) -> str:
        """Human-readable label for a mod: display name, or its folder name.

        Native mods (folder following the ``<Category>__<Mod>`` convention) are
        qualified with their engine path; any other enabled mod is labelled by the
        ``Name`` from its own ``ModuleInfo.txt`` when present, else its folder name.
        """
        mod = modlist.getMod(name)
        engine_path = mod_name_to_engine_path(name)
        if engine_path is not None:
            module_info = Path(mod.absolutePath()) / engine_path / "ModuleInfo.txt"
            display = read_mod_display_name(module_info)
            return f"{display or name} ({engine_path})"
        module_info = Path(mod.absolutePath()) / "ModuleInfo.txt"
        display = read_mod_display_name(module_info)
        return display or name

    def _save_files(self, saves_dir: Path) -> list[Path]:
        """Return the existing ``.sav`` files in the game's saves directory."""
        if not saves_dir.is_dir():
            return []
        return sorted(
            p for p in saves_dir.iterdir() if p.is_file() and p.suffix == ".sav"
        )

    def display(self) -> None:
        game = self._organizer.managedGame()
        if not game:
            self._notify("No game is being managed.", QMessageBox.Icon.Warning)
            return
        modlist = self._organizer.modList()

        mod_names = self._enabled_mods(modlist)
        mod_items: list[tuple[str, object]] = [(_NONE_MOD, None)]
        for name in mod_names:
            mod_items.append((self._mod_label(modlist, name), name))

        save_paths = self._save_files(Path(game.savesDirectory().absolutePath()))
        save_items: list[tuple[str, object]] = [(_NONE_SAVE, None)]
        for path in save_paths:
            save_items.append((path.name, path))

        dialog = QDialog(self._parentWidget())
        dialog.setWindowTitle(_NAME)
        dialog.setMinimumWidth(560)
        dialog.resize(620, 720)

        reporter_label = QLabel("Reporter:", dialog)
        reporter_edit = QLineEdit(dialog)
        reporter_edit.setText(_current_reporter(self._organizer))

        intro = QLabel(
            "Describe the mod bug you encountered in Space Rangers HD. Everything is "
            "optional — only what you fill in is included in the archive. The game "
            "version, the last run's log, and the technical files are always attached."
        )
        intro.setWordWrap(True)

        mod_combo = _filterable_combo(dialog, mod_items)
        save_combo = _filterable_combo(dialog, save_items)

        # --- Section: What happened ----------------------------------------
        what_box = QGroupBox("What happened", dialog)
        what_layout = QVBoxLayout(what_box)
        what_text = QPlainTextEdit(what_box)
        what_text.setPlaceholderText(
            "Briefly describe the problem in one or two lines, e.g. the game freezes "
            "when opening the planet map."
        )
        what_layout.addWidget(what_text)

        # --- Section: Where it happened ------------------------------------
        where_box = QGroupBox("Where it happened", dialog)
        where_layout = QVBoxLayout(where_box)
        where_hint = QLabel(
            "Which save was involved? Pick from your existing saves, or leave unset. "
            "Type to filter."
        )
        where_hint.setWordWrap(True)
        where_layout.addWidget(where_hint)
        where_layout.addWidget(save_combo)

        # --- Section: How to reproduce -------------------------------------
        how_box = QGroupBox("How to reproduce", dialog)
        how_layout = QVBoxLayout(how_box)
        how_hint = QLabel(
            "Detail the exact steps so it can be reproduced: what you did, in what "
            "order, and what happened."
        )
        how_hint.setWordWrap(True)
        how_layout.addWidget(how_hint)
        how_text = QPlainTextEdit(how_box)
        how_text.setPlaceholderText(
            "Step by step: 1. Start a new game…  2. …  3. The problem appears."
        )
        how_layout.addWidget(how_text)

        # --- Section: Suspected mod ----------------------------------------
        who_box = QGroupBox("Suspected mod", dialog)
        who_layout = QVBoxLayout(who_box)
        who_hint = QLabel(
            "Pick the mod you believe is causing the problem — this bug report is "
            "sent to that mod's author. Choose from the enabled mods, or leave "
            "unset if you're not sure. Type to filter."
        )
        who_hint.setWordWrap(True)
        who_layout.addWidget(who_hint)
        who_layout.addWidget(mod_combo)

        # --- Section: Attachments (screenshots) ----------------------------
        shots_box, screenshots_getter = _attachments_group(
            dialog,
            "Attachments (screenshots)",
            "Attach screenshots of the issue if you have any. You can add 0, 1, or "
            "more image files from anywhere on your computer.",
            _SCREENSHOT_FILTER,
            seed=[],
            button_text="Add screenshots…",
        )

        # --- Section: Attachments (technical) ------------------------------
        tech_box, tech_getter = _attachments_group(
            dialog,
            "Attachments (technical)",
            "These files are collected automatically: the last run's log, the "
            "active profile's modlist, and the game's ModCFG. Remove any you don't "
            "want, or add other technical files (screenshots, logs, configs).",
            _TECH_FILTER,
            seed=self._technical_files(game),
        )

        # --- Scrollable body + buttons -------------------------------------
        content = QWidget(dialog)
        content_layout = QVBoxLayout(content)
        for box in (what_box, where_box, how_box, who_box, shots_box, tech_box):
            content_layout.addWidget(box)
        content_layout.addStretch()

        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            dialog,
        )
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        if save_button is not None:
            save_button.setText("Save archive")
        buttons.accepted.connect(dialog.accept)  # type: ignore
        buttons.rejected.connect(dialog.reject)  # type: ignore

        layout = QVBoxLayout(dialog)
        reporter_row = QHBoxLayout()
        reporter_row.addWidget(reporter_label)
        reporter_row.addWidget(reporter_edit, 1)
        layout.addLayout(reporter_row)
        layout.addWidget(intro)
        layout.addWidget(scroll, 1)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        mod_name = _combo_data(mod_combo)
        save_path = _combo_data(save_combo)
        screenshots = screenshots_getter()
        tech_files = tech_getter()
        report = self._build_report(
            game,
            modlist,
            reporter_edit.text(),
            mod_name if isinstance(mod_name, str) else "",
            save_path if isinstance(save_path, Path) else None,
            what_text.toPlainText(),
            how_text.toPlainText(),
            screenshots,
            tech_files,
        )
        self._save_archive(
            game,
            report,
            modlist,
            reporter_edit.text(),
            mod_name if isinstance(mod_name, str) else "",
            save_path if isinstance(save_path, Path) else None,
            screenshots,
            tech_files,
        )

    # --- Report + archive --------------------------------------------------

    def _build_report(
        self,
        game: mobase.IPluginGame,
        modlist: mobase.IModList,
        reporter: str,
        mod_name: str,
        save_path: Path | None,
        what_text: str,
        how_text: str,
        screenshots: list[Path],
        tech_files: list[Path],
    ) -> str:
        """Compose the human-readable ``report.txt`` contents."""
        lines: list[str] = [
            "Space Rangers HD - Mod bug report",
            f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Reporter: {reporter.strip() or '(not provided)'}",
            "",
            f"Game version: {game.gameVersion()}",
        ]
        span = run_span(self._log_path(game))
        lines.append(
            f"Last run: {span[0]} - {span[1]}"
            if span is not None
            else "Last run: (timestamps unavailable)"
        )
        lines.append("")
        lines.append("What happened:")
        lines.append(what_text.strip() or "(not provided)")
        lines.append("")
        lines.append("Where it happened:")
        lines.append(save_path.name if save_path else "(not selected)")
        lines.append("")
        lines.append("How to reproduce:")
        lines.append(how_text.strip() or "(not provided)")
        lines.append("")
        lines.append("Suspected mod:")
        lines.append(self._mod_label_for_report(modlist, mod_name) or "(not selected)")
        lines.append("")
        shot_names = ", ".join(p.name for p in screenshots)
        lines.append("Attachments (screenshots):")
        lines.append(shot_names or "(none)")
        lines.append("")
        lines.append("Attachments (technical):")
        lines.append(", ".join(p.name for p in tech_files))
        return "\n".join(lines)

    def _technical_files(self, game: mobase.IPluginGame) -> list[Path]:
        """Files collected automatically and offered in the technical attachment list.

        The last run's log, the active profile's ``modlist.txt``, and the game's
        ``ModCFG.txt``. The user may remove or extend this list; each file is stored
        in the archive under its own file name.
        """
        profile_dir = Path(self._organizer.profile().absolutePath())
        game_dir = Path(game.dataDirectory().absolutePath())
        return [
            self._log_path(game),
            profile_dir / "modlist.txt",
            game_dir / "ModCFG.txt",
        ]

    def _mod_label_for_report(self, modlist: mobase.IModList, mod_name: str) -> str:
        if not mod_name:
            return _NONE_MOD
        mod = modlist.getMod(mod_name)
        label = self._mod_label(modlist, mod_name)
        if mod.version().isValid():
            label += f"  v{mod.version().displayString()}"
        return label

    def _log_path(self, game: mobase.IPluginGame) -> Path:
        return Path(game.documentsDirectory().absolutePath()) / "########.log"

    def _save_archive(
        self,
        game: mobase.IPluginGame,
        report: str,
        modlist: mobase.IModList,
        reporter: str,
        mod_name: str,
        save_path: Path | None,
        screenshots: list[Path],
        tech_files: list[Path],
    ) -> None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        name_parts = [f"spacerangershd-mod-bugreport-{stamp}"]
        if reporter.strip():
            name_parts.append(_filename_slug(reporter))
        if mod_name.strip():
            name_parts.append(_filename_slug(mod_name))
        default_name = "-".join(name_parts) + ".zip"
        dest, _filter = QFileDialog.getSaveFileName(
            self._parentWidget(),
            "Save mod bug-report archive",
            str(Path.home() / default_name),
            "ZIP archive (*.zip)",
        )
        if not dest:
            return
        if not dest.lower().endswith(".zip"):
            dest += ".zip"

        log_path = self._log_path(game)
        try:
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(_REPORT_FILENAME, report)
                for path in tech_files:
                    if path == log_path:
                        if path.is_file():
                            log_text = read_log(path)
                            archive.writestr(
                                path.name,
                                log_text
                                if log_text is not None
                                else "(the last run's log could not be read)",
                            )
                        else:
                            archive.writestr(
                                path.name,
                                "(the last run's log could not be read)",
                            )
                        continue
                    if path.is_file():
                        try:
                            archive.write(str(path), path.name)
                        except OSError:
                            continue
                if mod_name:
                    self._zip_mod(archive, modlist, mod_name)
                if save_path and save_path.is_file():
                    archive.write(str(save_path), f"saves/{save_path.name}")
                for path in screenshots:
                    if not path.is_file():
                        continue
                    try:
                        archive.write(str(path), f"screenshots/{path.name}")
                    except OSError:
                        continue
        except OSError as exc:
            self._notify(
                f"Could not write the archive:\n{exc}", QMessageBox.Icon.Warning
            )
            return

        self._notify(f"Mod bug-report archive saved to:\n{dest}")

    def _zip_mod(
        self, archive: zipfile.ZipFile, modlist: mobase.IModList, mod_name: str
    ) -> None:
        """Add the chosen mod's copy (from the MO2 mods directory) to the archive."""
        mod = modlist.getMod(mod_name)
        mod_root = Path(mod.absolutePath())
        prefix = f"mod/{mod_name}"
        if not mod_root.is_dir():
            return
        for path in mod_root.rglob("*"):
            if not path.is_file():
                continue
            try:
                archive.write(
                    str(path), f"{prefix}/{path.relative_to(mod_root).as_posix()}"
                )
            except OSError:
                continue

    def _notify(
        self, text: str, icon: QMessageBox.Icon = QMessageBox.Icon.Information
    ) -> None:
        box = QMessageBox(self._parentWidget())
        box.setWindowTitle(_NAME)
        box.setIcon(icon)
        box.setText(text)
        box.exec()
