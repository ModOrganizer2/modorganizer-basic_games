# -*- encoding: utf-8 -*-
from __future__ import annotations

import fnmatch
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, fields
from typing import Optional


import mobase


def convert_entry_to_tree(entry: mobase.FileTreeEntry) -> Optional[mobase.IFileTree]:
    if not entry.isDir():
        return None
    if isinstance(entry, mobase.IFileTree):
        return entry
    if (parent := entry.parent()) is None:
        return None
    converted_entry = parent.find(
        entry.name(), mobase.FileTreeEntry.FileTypes.DIRECTORY
    )
    if isinstance(converted_entry, mobase.IFileTree):
        return converted_entry
    return None


@dataclass
class FileRegexPatterns:
    """Regex pattern matching the file glob patterns in `FilePatterns`."""

    set_as_root: Optional[re.Pattern] = None
    valid: Optional[re.Pattern] = None
    delete: Optional[re.Pattern] = None
    move: Optional[re.Pattern] = None

    @classmethod
    def from_file_patterns(cls, file_patterns: FilePatterns) -> FileRegexPatterns:
        """Returns an instance of `FileRegexPatterns`,
        with the file list fields from `FilePatterns` as regex patterns.
        """
        return cls(
            **{
                f.name: (
                    cls.file_glob_list_regex(value)
                    if (value := getattr(file_patterns, f.name))
                    else None
                )
                for f in fields(cls)
            }
        )

    @staticmethod
    def file_glob_list_regex(file_list: Iterable[str]) -> re.Pattern:
        """Returns a regex pattern for a file list with glob patterns.

        Every pattern has a capturing group,
        so that `match.lastindex - 1` will give the `file_list` index.
        """
        return re.compile(
            f'(?:{"|".join(f"({fnmatch.translate(f)})" for f in file_list)})', re.I
        )


@dataclass
class FilePatterns:
    """File definitions for the `BasicGameModDataChecker`.
    Glob pattern supported (without subfolders).

    Match files / folders with e.g. `.regex.move.match`.
    Fields match `.regex`.
    """

    set_as_root: Optional[Iterable[str]] = None
    """If a folder from this set is found, it will be set as new root dir (unfolded) and
    its contents are checked again.
    """

    valid: Optional[Iterable[str]] = None
    """Files and folders in the right path.
    Check result: `mobase.ModDataChecker.VALID`.
    """

    delete: Optional[Iterable[str]] = None
    """Files/folders to delete. Check result:: `mobase.ModDataChecker.FIXABLE`."""

    move: Optional[dict[str, str]] = None
    """Files/folders to move and their target.

    If the path ends with `/` or `\\`, the entry will be inserted
    in the corresponding directory instead of replacing it.

    Check result: `mobase.ModDataChecker.FIXABLE`.

    Example::

        {"*.ext": "path/to/target_folder/"}

    See Also:
        `mobase.IFileTree.move`
    """

    regex: FileRegexPatterns = field(init=False)
    """The regex patterns derived from the file (glob) patterns."""
    _move_targets: Sequence[str] = field(init=False, repr=False)

    def __post_init__(self):
        self.update_regex()

    def update_regex(self):
        """Update regex after init field changes."""
        self.regex = FileRegexPatterns.from_file_patterns(self)
        if self.move:
            self._move_targets = list(self.move.values())

    def find_move_target(self, file_name: str) -> Optional[str]:
        """Find a matching pattern (key) from `.move` and return its (value) matching the

        Args:
            match_index: Either the match from `.regex.move.match` or the index
                of the move target = matched group index - 1.
        """
        if (
            self.regex.move
            and (match := self.regex.move.match(file_name))
            and (i := match.lastindex) is not None
        ):
            return self._move_targets[i - 1]
        return None


class BasicModDataChecker(mobase.ModDataChecker):
    """Game feature that is used to check and fix the content of a data tree
    via simple glob files patterns (without subfolders).
    """

    file_patterns: FilePatterns

    def __init__(self, file_patterns: FilePatterns):
        super().__init__()
        self.file_patterns = file_patterns

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        status = mobase.ModDataChecker.INVALID
        for entry in filetree:
            name = entry.name().casefold()
            regex = self.file_patterns.regex
            if regex.set_as_root and regex.set_as_root.match(name):
                return mobase.ModDataChecker.FIXABLE
            elif regex.valid and regex.valid.match(name):
                if status is not mobase.ModDataChecker.FIXABLE:
                    status = mobase.ModDataChecker.VALID
            elif (regex.move and regex.move.match(name)) or (
                regex.delete and regex.delete.match(name)
            ):
                status = mobase.ModDataChecker.FIXABLE
            else:
                return mobase.ModDataChecker.INVALID
        return status

    def fix(self, filetree: mobase.IFileTree) -> Optional[mobase.IFileTree]:
        for entry in list(filetree):
            name = entry.name().casefold()
            regex = self.file_patterns.regex
            if regex.set_as_root and regex.set_as_root.match(name):
                new_root = convert_entry_to_tree(entry)
                return self.fix(new_root) if new_root else None
            elif regex.valid and regex.valid.match(name):
                continue
            elif regex.delete and regex.delete.match(name):
                entry.detach()
            elif regex.move:
                move_target = self.file_patterns.find_move_target(name)
                if move_target is not None:
                    filetree.move(entry, move_target)
        return filetree
