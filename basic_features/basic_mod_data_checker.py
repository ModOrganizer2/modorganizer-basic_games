# -*- encoding: utf-8 -*-
from __future__ import annotations

import fnmatch
import re
import sys
from collections.abc import Iterable, Sequence
from typing import ClassVar, MutableMapping, Optional, TypedDict

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
        if pattern := self.get(key):
            return self.match_index_of_pattern(search_str, pattern)
        return None

    @staticmethod
    def match_index_of_pattern(search_str: str, pattern: re.Pattern) -> Optional[int]:
        """Get the index of the matched group if `search_str` matches `pattern`
        (from this dict).

        Returns:
            The 0-based index of the matched group or None for no match.
        """
        if (match := pattern.match(search_str)) and match.lastindex:
            return match.lastindex - 1
        return None

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

    The file definitions support glob pattern (without subfolders) and are
    checked and fixed in definition order of the `file_patterns` dict.

    Args:
        file_patterns (optional): A dict (GlobPatternDict) with the following keys::

            {
                "unfold": [ "list of folders to unfold" ],
                    # (remove and move contents to parent), after being checked and
                    # fixed recursively.
                    # Check result: `mobase.ModDataChecker.VALID`.

                "valid": [ "list of files and folders in the right path." ],
                    # Check result: `mobase.ModDataChecker.VALID`.

                "delete": [ "list of files/folders to delete." ],
                    # Check result: `mobase.ModDataChecker.FIXABLE`.

                "move": {"Files/folders to move": "target path"}
                    # If the path ends with `/` or `\\`, the entry will be inserted
                    # in the corresponding directory instead of replacing it.
                    # Check result: `mobase.ModDataChecker.FIXABLE`.
            }

        Example::

            BasicModDataChecker(
                {
                    "valid": ["valid_folder", "*.ext1"]
                    "move": {"*.ext2": "path/to/target_folder/"}
                }
            )

    See Also:
        `mobase.IFileTree.move` for the `"move"` target path specs.
    """

    default_file_patterns: ClassVar[GlobPatternDict] = {}
    """Default for `file_patterns` - for subclasses."""

    _file_patterns: GlobPatternDict
    """Private `file_patterns`, updated together with `._regex` and `._move_targets`."""

    _regex: RegexPatternDict
    """The regex patterns derived from the file (glob) patterns."""

    _move_targets: Sequence[str]
    """Target paths from `file_patterns["move"]`."""

    def __init__(self, file_patterns: Optional[GlobPatternDict] = None):
        super().__init__()
        # Init with copy from class var by default (for unique instance var).
        self.set_patterns(file_patterns or (self.default_file_patterns.copy()))

    def set_patterns(self, file_patterns: GlobPatternDict):
        """Sets the file patterns, replacing previous/default values and order."""
        self._file_patterns = file_patterns
        self.update_patterns()

    def update_patterns(self, file_patterns: Optional[GlobPatternDict] = None):
        """Update file patterns. Preserves previous/default definition
        (check/fix) order.
        """
        if file_patterns:
            self._file_patterns.update(file_patterns)
        self._regex = RegexPatternDict.from_glob_patterns(self._file_patterns)
        if move_map := self._file_patterns.get("move"):
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
                        return None
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
