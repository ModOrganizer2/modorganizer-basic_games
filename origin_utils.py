# -*- encoding: utf-8 -*-

# Heavily influenced by https://github.com/erri120/GameFinder

import os

from pathlib import Path
from typing import Dict
from urllib import parse

from PyQt5.QtCore import QDir, QFileInfo, QStandardPaths


def find_games() -> Dict[str, Path]:
    """
    Find the list of Origin games installed.

    Returns:
        A mapping from Origin manifest IDs to install locations for available
        Origin games.
    """
    games: Dict[str, Path] = {}
    
    local_content_path = Path(os.path.expandvars("%PROGRAMDATA%")).joinpath("Origin", "LocalContent")
    for manifest in local_content_path.glob("**/*.mfst"):
        # Skip any manifest file with '@steam'
        if '@steam' in manifest.name.lower():
            continue

        # Read the file and look for &id= and &dipinstallpath=
        with open(manifest, 'r') as f:
            manifest_query = f.read()
        url = parse.urlparse(manifest_query)
        query = parse.parse_qs(url.query)
        if 'id' not in query:
            # If id is not present, we have no clue what to do.
            continue
        if 'dipinstallpath' not in query:
            # We could query the Origin server for the install location but... no?
            continue
        
        for id_ in query['id']:
            for path_ in query['dipinstallpath']:
                games[id_] = Path(path_)
        
    return games

if __name__ == "__main__":
    games = find_games()
    for k, v in games.items():
        print("Found game with id {} at {}.".format(k, v))