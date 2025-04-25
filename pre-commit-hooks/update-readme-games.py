import ast
import logging
from pathlib import Path
from typing import TypedDict, cast

from jinja2 import Template

START_TAG = "<!-- START: GAMES -->"
END_TAG = "<!-- END: GAMES -->"

_FILE = Path(__file__)
ROOT = _FILE.parent.parent
TPLT = _FILE.with_suffix(".jinja")

# careful with the new lines here
HEADER = """
<!-- This section was automatically generated, do not edit! -->

| Game | Author | File | Extras |
|------|--------|------|--------|
"""
FOOTER = """
"""

CUSTOM_AUTHOR_HOMEPAGES = {
    "Luca/EzioTheDeadPoet": "https://eziothedeadpoet.github.io/AboutMe/",
    "R3z Shark": "",
    "Miner Of Worlds": "",
    "Kane Dou": "",
    "Ryan Young": "",
    "The Conceptionist": "",
}


class Author(TypedDict):
    name: str
    homepage: str


class BasicGameInformation(TypedDict, total=False):
    name: str
    authors: list[Author]
    file: str


def extract_basic_games(path: Path):
    logging.info(f"extracting basic games from {path}...")
    with open(path, "r") as fp:
        module = ast.parse(fp.read())

    games: list[ast.ClassDef] = []
    for stmt in module.body:
        if not isinstance(stmt, ast.ClassDef):
            continue

        for base in stmt.bases:
            if isinstance(base, ast.Name) and base.id == "BasicGame":
                games.append(stmt)
                break

            # not sure if this is possible? would mean something like xxx.BasicGame
            if isinstance(base, ast.Attribute) and base.attr == "BasicGame":
                games.append(stmt)
                break

    return games


def extract_basic_game_information(path: Path, game: ast.ClassDef):
    value: BasicGameInformation = {
        "file": "https://github.com/ModOrganizer/modorganizer-basic_games/blob/master/"
        + path.relative_to(ROOT).as_posix()
    }
    for stmt in game.body:
        if not isinstance(stmt, ast.Assign):
            continue

        # skip multiple assignments (should not be any in a class?)
        if len(stmt.targets) != 1:
            continue

        target = stmt.targets[0]
        if not isinstance(target, ast.Name):  # can this happen?
            continue

        match target.id:
            case "GameName":
                assert isinstance(stmt.value, ast.Constant)
                value["name"] = stmt.value.value
            case "Author":
                assert isinstance(stmt.value, ast.Constant)
                author_s = cast(str, stmt.value.value)

                authors = [p.strip() for p in author_s.split(",")]
                authors = [p.strip() for pp in authors for p in pp.split("&")]
                value["authors"] = sorted(
                    [
                        {
                            "name": author,
                            "homepage": CUSTOM_AUTHOR_HOMEPAGES.get(
                                author, f"https://github.com/{author}"
                            ),
                        }
                        for author in authors
                    ],
                    key=lambda a: a["name"],
                )
            case _:
                pass

        print(stmt, stmt.value, target.id)
    return value


def generate_table():
    # list the games
    games: list[tuple[Path, ast.ClassDef]] = []
    for path in ROOT.joinpath("games").glob("**/*.py"):
        if path.parent.name == "quarantine":
            continue

        games.extend((path, game) for game in extract_basic_games(path))

    infos = [extract_basic_game_information(path, game) for path, game in games]

    with open(TPLT, "r") as fp:
        template = Template(fp.read())

    content = template.render(games=sorted(infos, key=lambda g: g.get("name", "")))

    return HEADER + content + FOOTER


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # read the README content
    with open(ROOT.joinpath("README.md"), "r") as fp:
        readme = fp.read()

    # find the start and end block
    start = readme.find(START_TAG)
    end = readme.find(END_TAG)
    assert start >= 0 and end >= 0

    readme = readme[:start] + START_TAG + "\n" + generate_table() + readme[end:]

    with open(ROOT.joinpath("README2.md"), "w") as fp:
        fp.write(readme)
