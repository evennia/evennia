"""
Convert contribs' README files to proper documentation pages along with
an index.

"""
from collections import defaultdict
from os.path import abspath, dirname, join as pathjoin, sep
from glob import glob

_EVENNIA_PATH = pathjoin(dirname(dirname(dirname(abspath(__file__)))))
_DOCS_PATH = pathjoin(_EVENNIA_PATH, "docs")

_SOURCE_DIR = pathjoin(_EVENNIA_PATH, "evennia", "contrib")
_OUT_DIR = pathjoin(_DOCS_PATH, "source", "Contribs")
_OUT_INDEX_FILE = pathjoin(_OUT_DIR, "Contrib-Overview.md")


_CATEGORY_DESCS = {
    "base_systems": """
This category contains systems that are not necessarily tied to a specific
in-game mechanic but is useful for the game as a whole. Examples include
login systems, new command syntaxes, and build helpers.
    """,
    "full_systems": """
This category contains 'complete' game engines that can be used directly
to start creating content without no further additions (unless you want to).
""",
    "game_systems": """
This category holds code implementing in-game gameplay systems like
crafting, mail, combat and more. Each system is meant to be adopted
piecemeal and adopted for your game. This does not include
roleplaying-specific systems, those are found in the `rpg` folder.
""",
    "grid": """
Systems related to the game world's topology and structure. This has
contribs related to rooms, exits and map building.
""",
    "rpg": """
These are systems specifically related to roleplaying
and rule implementation like character traits, dice rolling and emoting.
""",
    "tutorials": """
Helper resources specifically meant to teach a development concept or
to exemplify an Evennia system. Any extra resources tied to documentation
tutorials are found here. Also the home of the Tutorial World demo adventure.
""",
    "utils": """
Miscellaneous, optional tools for manipulating text, auditing connections
and more.
"""
}


_FILENAME_MAP = {
    "rpsystem": "RPSystem",
    "xyzgrid": "XYZGrid",
    "awsstorage": "AWSStorage"
}

HEADER = """# Contribs

_Contribs_ are optional code snippets and systems contributed by
the Evennia community. They vary in size and complexity and
may be more specific about game types and styles than 'core' Evennia.
This page is auto-generated and summarizes all contribs currently included.

All contrib categories are imported from `evennia.contrib`, such as

    from evennia.contrib.base_systems import building_menu

Each contrib contains installation instructions for how to integrate it
with your other code. If you want to tweak the code of a contrib, just
copy its entire folder to your game directory and modify/use it from there.

If you want to contribute yourself, see [here](Contributing)!

> Hint: Additional (potentially un-maintained) code snippets from the community can be found
in our discussion forum's [Community Contribs & Snippets](https://github.com/evennia/evennia/discussions/categories/community-contribs-snippets) category.

"""


TOCTREE = """
```{{toctree}}
:depth: 2

{listing}

"""

CATEGORY = """
## {category}

_{category_desc}_

{blurbs}


"""

BLURB = """
### Contrib: `{name}`

{credits}

{blurb}

[Read the documentation]({filename})

"""

FOOTER = """

----

<small>This document page is generated from `{path}`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
"""

INDEX_FOOTER = """

----

<small>This document page is auto-generated from the sources. Manual changes
will be overwritten.</small>
"""


def readmes2docs(directory=_SOURCE_DIR):
    """
    Parse directory for README files and convert them to doc pages.

    """

    ncount = 0
    categories = defaultdict(list)

    glob_path = f"{directory}{sep}*{sep}*{sep}README.md"

    for file_path in glob(glob_path):
        # paths are e.g. evennia/contrib/utils/auditing/README.md
        _, category, name, _ = file_path.rsplit(sep, 3)

        filename = "Contrib-" + "-".join(
            _FILENAME_MAP.get(
                part, part.capitalize() if part[0].islower() else part)
            for part in name.split("_")) + ".md"
        outfile = pathjoin(_OUT_DIR, filename)

        with open(file_path) as fil:
            data = fil.read()

        clean_file_path = f"evennia{sep}contrib{file_path[len(directory):]}"
        data += FOOTER.format(path=clean_file_path)

        try:
            credits = data.split("\n\n", 3)[1]
            blurb = data.split("\n\n", 3)[2]
        except IndexError:
            blurb = name

        with open(outfile, 'w') as fil:
            fil.write(data)

        categories[category].append((name, credits, blurb, filename))
        ncount += 1

    # build the index with blurbs

    lines = [HEADER]
    filenames = []
    for category in sorted(categories):
        contrib_tups = categories[category]
        catlines = []
        for tup in sorted(contrib_tups, key=lambda tup: tup[0].lower()):
            catlines.append(
                BLURB.format(
                    name=tup[0],
                    credits=tup[1],
                    blurb=tup[2],
                    filename=tup[3],
                )
            )
            filenames.append(f"Contribs{sep}{tup[3]}")
        lines.append(
            CATEGORY.format(
                category=category,
                category_desc=_CATEGORY_DESCS[category].strip(),
                blurbs="\n".join(catlines)
            )
        )
    lines.append(TOCTREE.format(
        listing="\n".join(filenames))
    )

    lines.append(INDEX_FOOTER)

    text = "\n".join(lines)



    with open(_OUT_INDEX_FILE, 'w') as fil:
        fil.write(text)

    print(f"  -- Converted Contrib READMEs to {ncount} doc pages + index.")


if __name__ == "__main__":
    readmes2docs(_SOURCE_DIR)
