# -*- encoding: utf-8 -*-
from __future__ import annotations

import fnmatch
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, fields
from typing import Optional, Protocol


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


class HasGlobPatterns(Protocol):
    set_as_root: Optional[Iterable[str]]
    valid: Optional[Iterable[str]]
    delete: Optional[Iterable[str]]
    move: Optional[Iterable[str]]


@dataclass
class FileRegexPatterns:
    """Regex patterns for validation in `BasicModDataChecker`."""

    set_as_root: Optional[re.Pattern] = None
    valid: Optional[re.Pattern] = None
    delete: Optional[re.Pattern] = None
    move: Optional[re.Pattern] = None

    @classmethod
    def from_glob_patterns(cls, glob_patterns: HasGlobPatterns) -> FileRegexPatterns:
        """Returns an instance of `FileRegexPatterns`,
        with the glob pattern fields in `glob_patterns` translated to regex.
        """
        return cls(
            **{
                f.name: (
                    cls.regex_from_glob_list(value)
                    if (value := getattr(glob_patterns, f.name))
                    else None
                )
                for f in fields(FileRegexPatterns)
            }
        )

    @staticmethod
    def regex_from_glob_list(glob_list: Iterable[str]) -> re.Pattern:
        """Returns a regex pattern form a list of glob patterns.

        Every pattern has a capturing group,
        so that `match.lastindex - 1` will give the `file_list` index.
        """
        return re.compile(
            f'(?:{"|".join(f"({fnmatch.translate(f)})" for f in glob_list)})', re.I
        )

    @staticmethod
    def get_match_index(search_str: str, pattern: re.Pattern) -> Optional[int]:
        """Get the index of the matched group if `search_str` matches `pattern`.

        Args:
            search_str: the string to search
            pattern: a pattern from `FileRegexPatterns`.

        Returns:
            The 0-based index of the matched group or None for no match.
        """
        if not (match := pattern.match(search_str)) or match.lastindex is None:
            return None
        return match.lastindex - 1


@dataclass
class BasicModDataChecker(mobase.ModDataChecker):
    """Game feature that is used to check and fix the content of a data tree
    via simple file definitions.

    The file definitions support glob pattern (without subfolders) and are checked in
    order.
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
    """Files/folders to delete. Check result: `mobase.ModDataChecker.FIXABLE`."""

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

    _regex: FileRegexPatterns = field(init=False, repr=False)
    """The regex patterns derived from the file (glob) patterns."""

    _move_targets: Sequence[str] = field(init=False, repr=False)

    def __post_init__(self):
        self.update_patterns()

    def update_patterns(self):
        """Update patterns after init field changes."""
        self._regex = FileRegexPatterns.from_glob_patterns(self)
        if self.move:
            self._move_targets = list(self.move.values())

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        status = mobase.ModDataChecker.INVALID
        for entry in filetree:
            name = entry.name().casefold()
            regex = self._regex
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
            regex = self._regex
            if regex.set_as_root and regex.set_as_root.match(name):
                new_root = convert_entry_to_tree(entry)
                return self.fix(new_root) if new_root else None
            elif regex.valid and regex.valid.match(name):
                continue
            elif regex.delete and regex.delete.match(name):
                entry.detach()
            elif regex.move:
                move_target = self._find_move_target(name)
                if move_target is not None:
                    filetree.move(entry, move_target)
        return filetree

    def _find_move_target(self, filename: str) -> Optional[str]:
        """Find a matching file pattern (key) from `.move` and return the target (value).

        Args:
            filename: the file name to match.

        Returns:
            The move target or None for no match or no `.move` pattern.
        """
        if (
            self._regex.move
            and (i := self._regex.get_match_index(filename, self._regex.move))
            is not None
        ):
            return self._move_targets[i]
        return None
