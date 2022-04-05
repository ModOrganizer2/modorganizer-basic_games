# -*- encoding: utf-8 -*-
from __future__ import annotations

import fnmatch
import re
import sys
from collections.abc import Iterable, Sequence
from typing import MutableMapping, Optional, TypedDict, overload

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


class RegexPatternDict(dict, MutableMapping[str, re.Pattern]):
    """Regex patterns for validation in `BasicModDataChecker`."""

    @classmethod
    def from_glob_patterns(cls, glob_patterns: GlobPatternDict) -> RegexPatternDict:
        """Returns an instance of `RegexPatternDict`, with the `glob_patterns`
        translated to regex.
        """
        return cls(
            (
                key,
                cls.regex_from_glob_list(value)
                if isinstance(value, Iterable)
                else None,
            )
            for key, value in glob_patterns.items()
        )

    def get_match_index(self, key: str, search_str: str) -> Optional[int]:
        """Get the index of the matched group if the `self[key]` matches `search_str`.

        Returns:
            The 0-based index of the matched group or None for no match.
        """
        if (pattern := self.get(key)) is None:
            return None
        else:
            return self.match_index_of_pattern(search_str, pattern)

    @staticmethod
    def match_index_of_pattern(search_str: str, pattern: re.Pattern) -> Optional[int]:
        """Get the index of the matched group if `search_str` matches `pattern`
        (from this dict).

        Returns:
            The 0-based index of the matched group or None for no match.
        """
        if not (match := pattern.match(search_str)) or match.lastindex is None:
            return None
        return match.lastindex - 1

    @staticmethod
    def regex_from_glob_list(glob_list: Iterable[str]) -> re.Pattern:
        """Returns a regex pattern form a list of glob patterns.

        Every pattern has a capturing group, so that `match.lastindex - 1` will
        give the `glob_list` index.
        """
        return re.compile(
            f'(?:{"|".join(f"({fnmatch.translate(f)})" for f in glob_list)})', re.I
        )


class GlobPatternDict(TypedDict, total=False):
    """See: `BasicModDataChecker`"""

    unfold: Iterable[str] | None
    valid: Iterable[str] | None
    delete: Iterable[str] | None
    move: MutableMapping[str, str] | None


class BasicModDataChecker(mobase.ModDataChecker):
    """Game feature that is used to check and fix the content of a data tree
    via simple file definitions.

    The file definitions support glob pattern (without subfolders) and are checked in
    definition order (passed either as dict or kwargs).

    Args:
        file_patterns (optional): An dict with the keys below or as kwargs:

        unfold (optional): Folders to unfold (remove and move contents to parent),
            after being checked and fixed recursively.

        valid (optional): Files and folders in the right path.
            Check result: `mobase.ModDataChecker.VALID`.

        delete (optional): Files/folders to delete.
            Check result: `mobase.ModDataChecker.FIXABLE`.

        move (optional): Files/folders to move and their target.
            If the path ends with `/` or `\\`, the entry will be inserted
            in the corresponding directory instead of replacing it.

            Check result: `mobase.ModDataChecker.FIXABLE`.

        Example::

            BasicModDataChecker(
                valid=["valid_folder", "*.ext1"]
                move={"*.ext2": "path/to/target_folder/"}
            )

            BasicModDataChecker(
                {
                    "valid": ["valid_folder", "*.ext1"],
                    "move": {"*.ext2": "path/to/target_folder/"}
                }
            )

    See Also:
        `mobase.IFileTree.move`
    """

    file_patterns = None  # type: GlobPatternDict
    """Use `update_patterns` for modifications."""

    _regex: RegexPatternDict
    """The regex patterns derived from the file (glob) patterns."""

    _move_targets: Sequence[str]

    # Overloads as workaround for **kwargs: Unpack[GlobPatternDict]
    @overload
    def __init__(
        self,
        *,
        unfold: Iterable[str] | None = None,
        valid: Iterable[str] | None = None,
        delete: Iterable[str] | None = None,
        move: dict[str, str] | None = None,
    ):
        ...

    @overload
    def __init__(
        self,
        file_patterns: Optional[GlobPatternDict] = None,
        *,
        unfold: Iterable[str] | None = None,
        valid: Iterable[str] | None = None,
        delete: Iterable[str] | None = None,
        move: dict[str, str] | None = None,
    ):
        ...

    def __init__(
        self, file_patterns: Optional[GlobPatternDict] = None, **kwargs
    ):  # Unpack[GlobPatternDict]
        super().__init__()
        # Init with copy from class var
        self.file_patterns = fp.copy() if (fp := self.file_patterns) else {}
        self.update_patterns(file_patterns, **kwargs)

    @overload
    def update_patterns(
        self,
        *,
        unfold: Iterable[str] | None = None,
        valid: Iterable[str] | None = None,
        delete: Iterable[str] | None = None,
        move: dict[str, str] | None = None,
    ):
        ...

    @overload
    def update_patterns(
        self,
        file_patterns: Optional[GlobPatternDict] = None,
        *,
        unfold: Iterable[str] | None = None,
        valid: Iterable[str] | None = None,
        delete: Iterable[str] | None = None,
        move: dict[str, str] | None = None,
    ):
        ...

    def update_patterns(self, file_patterns=None, **kwargs):  # Unpack[GlobPatternDict]
        """Update file patterns."""
        if file_patterns:
            self.file_patterns.update(file_patterns)
        self.file_patterns.update(kwargs)
        self._regex = RegexPatternDict.from_glob_patterns(self.file_patterns)
        if move_map := self.file_patterns.get("move"):
            self._move_targets = list(move_map.values())

    def dataLooksValid(
        self, filetree: mobase.IFileTree
    ) -> mobase.ModDataChecker.CheckReturn:
        status = mobase.ModDataChecker.INVALID
        for entry in filetree:
            name = entry.name().casefold()
            for key, regex in self._regex.items():
                if not regex or not regex.match(name):
                    continue
                if key == "unfold":
                    return mobase.ModDataChecker.FIXABLE
                elif key == "valid":
                    if status is not mobase.ModDataChecker.FIXABLE:
                        status = mobase.ModDataChecker.VALID
                elif key in ("move", "delete"):
                    status = mobase.ModDataChecker.FIXABLE
                break
            else:
                return mobase.ModDataChecker.INVALID
        return status

    def fix(self, filetree: mobase.IFileTree) -> Optional[mobase.IFileTree]:
        print(f"{self.file_patterns}")
        print(self._regex)
        for entry in list(filetree):
            name = entry.name()
            # Fix entries in pattern definition order.
            for key, regex in self._regex.items():
                if not regex or not regex.match(name):
                    continue
                if key == "valid":
                    break
                elif key == "unfold":
                    if (folder_tree := convert_entry_to_tree(entry)) is not None:
                        if folder_tree:  # Not empty
                            # Recursively fix subtree and unfold.
                            if not (fixed_folder_tree := self.fix(folder_tree)):
                                return None
                            filetree.merge(fixed_folder_tree)
                        folder_tree.detach()
                    else:
                        print(f"Cannot unfold {name}!", file=sys.stderr)
                elif key == "delete":
                    entry.detach()
                elif key == "move":
                    if (move_target := self._get_move_target(name)) is not None:
                        filetree.move(entry, move_target)
                break
        return filetree

    def _get_move_target(self, filename: str) -> Optional[str]:
        if (i := self._regex.get_match_index("move", filename)) is None:
            return None
        return self._move_targets[i]
