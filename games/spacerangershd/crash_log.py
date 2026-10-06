# Copyright (c) 2026 ringill
# SPDX-License-Identifier: MIT

"""Reading SRHD's last-run crash log (``########.log``).

SRHD writes the current run's log to ``%Documents%\\SpaceRangersHD\\########.log``
(ASCII/ANSI text without a BOM, first line ``Start``); previous runs are archived
into ``Errors``. The crash indicator is a log line starting with ``Exception `` —
a clean run contains none, every crashed run ends with one.

These helpers read only the **last** run's log (``########.log``), never the
``Errors`` history: ``crash_tail`` returns the text from the first ``Exception``
line to end of file.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

# The log is ASCII/ANSI with no BOM. latin-1 decodes every byte losslessly so the
# tail text and the ``Exception`` marker are preserved exactly as on disk.
_ENCODING = "latin-1"

_CRASH_MARKER = "Exception "

# Human-readable local-time format for the run span (``2026-08-15 21:04:32``). The
# timestamps are formatted with ``datetime.fromtimestamp``, which converts to the
# client's local wall-clock time (its timezone and environment), not UTC/ISO.
_SPAN_FORMAT = "%Y-%m-%d %H:%M:%S"


def read_log(log_path: Path) -> str | None:
    """Return the full log text, or ``None`` when the file is missing/unreadable."""
    try:
        return log_path.read_text(encoding=_ENCODING, errors="replace")
    except OSError:
        return None


def crash_tail(log_path: Path) -> str | None:
    """Return the log text from the first ``Exception`` line to end of file.

    Returns ``None`` when the log is missing/unreadable, or when it contains no
    line starting with ``Exception `` (a clean run). The returned string keeps the
    original line breaks; trailing blank lines are stripped.
    """
    text = read_log(log_path)
    if text is None:
        return None
    lines = text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.startswith(_CRASH_MARKER)),
        None,
    )
    if start is None:
        return None
    return "\n".join(lines[start:]).rstrip()


def run_span(log_path: Path) -> tuple[str, str] | None:
    """Return ``(start, end)`` local timestamps of the run the log covers.

    ``start`` is the log file's creation time (the game's launch moment), ``end``
    its last modification time (the moment the run finished). Both are converted to
    the client's local wall-clock time via ``datetime.fromtimestamp``. Returns
    ``None`` when the file is missing or its times cannot be read.
    """
    try:
        created = os.path.getctime(log_path)
        modified = os.path.getmtime(log_path)
    except OSError:
        return None
    return (
        datetime.fromtimestamp(created).strftime(_SPAN_FORMAT),
        datetime.fromtimestamp(modified).strftime(_SPAN_FORMAT),
    )
