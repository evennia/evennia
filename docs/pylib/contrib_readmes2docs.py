"""
Convert contribs' README files to proper documentation pages along with
an index.

"""
from collections import defaultdict
from glob import glob
from os.path import abspath, dirname
from os.path import join as pathjoin
from os.path import sep

_EVENNIA_PATH = pathjoin(dirname(dirname(dirname(abspath(__file__)))))
_DOCS_PATH = pathjoin(_EVENNIA_PATH, "docs")

_SOURCE_DIR = pathjoin(_EVENNIA_PATH, "evennia", "contrib")
_OUT_DIR = pathjoin(_DOCS_PATH, "source", "Contribs")
_OUT_INDEX_FILE = pathjoin(_OUT_DIR, "Contribs-Overview.md")

_FILENAME_MAP = {"rpsystem": "RPSystem", "xyzgrid": "XYZGrid", "awsstorage": "AWSStorage"}

# ---------------------------------------------------------------------------------------------

_FILE_STRUCTURE = """{header}
{categories}
{footer}"""

_CATEGORY_DESCS = {
    "base_systems": """
Systems that are not necessarily tied to a specific
in-game mechanic but which are useful for the game as a whole. Examples include
login systems, new command syntaxes, and build helpers.
    """,
    "full_systems": """
'Complete' game engines that can be used directly to start creating content
without no further additions (unless you want to).
""",
    "game_systems": """
In-game gameplay systems like crafting, mail, combat and more.
Each system is meant to be adopted piecemeal and adopted for your game.
This does not include roleplaying-specific systems, those are found in
the `rpg` category.
""",
    "grid": """
Systems related to the game world's topology and structure. Contribs related
to rooms, exits and map building.
""",
    "rpg": """
Systems specifically related to roleplaying
and rule implementation like character traits, dice rolling and emoting.
""",
    "tutorials": """
Helper resources specifically meant to teach a development concept or
to exemplify an Evennia system. Any extra resources tied to documentation
tutorials are found here. Also the home of the Tutorial-World and Evadventure
demo codes.
""",
    "utils": """
Miscellaneous, tools for manipulating text, security auditing, and more.
""",
}


HEADER = """# Contribs

```{{sidebar}} More contributions
Additional Evennia code snippets and contributions can be found
in the [Community Contribs & Snippets][forum] forum.
```
_Contribs_ are optional code snippets and systems contributed by
the Evennia community. They vary in size and complexity and
may be more specific about game types and styles than 'core' Evennia.
This page is auto-generated and summarizes all **{ncontribs}** contribs currently included
with the Evennia distribution.

All contrib categories are imported from `evennia.contrib`, such as

    from evennia.contrib.base_systems import building_menu

Each contrib contains installation instructions for how to integrate it
with your other code. If you want to tweak the code of a contrib, just
copy its entire folder to your game directory and modify/use it from there.

If you want to add a contrib, see [the contrib guidelines](Contribs-Guidelines)!

[forum]: https://github.com/evennia/evennia/discussions/categories/community-contribs-snippets

## Index
{category_index}
{index}
"""


TOCTREE = """
```{{toctree}}
:hidden:
Contribs-Guidelines.md
```
```{{toctree}}
:maxdepth: 1

{listing}
```"""

CATEGORY = """
## {category}

_{category_desc}_

{toctree}

{blurbs}


"""

BLURB = """
### `{name}`

_{credits}_

{blurb}

[Read the documentation](./{filename}) - [Browse the Code](api:{code_location})

"""

FOOTER = """

----

<small>This document page is generated from `{path}`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
"""

INDEX_FOOTER = """

----

<small>This document page is auto-generated. Manual changes
will be overwritten.</small>
"""


def build_table(datalist, ncols):
    """Build a Markdown table-grid for compact display"""

    nlen = len(datalist)
    table_heading = "| " * (ncols) + "|"
    table_sep = "|---" * (ncols) + "|"
    table = ""
    for ir in range(0, nlen, ncols):
        table += "| " + " | ".join(datalist[ir : ir + ncols]) + " |\n"
    return f"{table_heading}\n{table_sep}\n{table}"


def readmes2docs(directory=_SOURCE_DIR):
    """
    Parse directory for README files and convert them to doc pages.

    """

    ncount = 0
    index = []
    category_index = []
    categories = defaultdict(list)

    glob_path = f"{directory}{sep}*{sep}*{sep}README.md"

    for file_path in glob(glob_path):
        # paths are e.g. evennia/contrib/utils/auditing/README.md
        _, category, name, _ = file_path.rsplit(sep, 3)

        index.append(f"[{name}](#{name.lower()})")
        category_index.append(f"[{category}](#{category.lower()})")

        pypath = f"evennia.contrib.{category}.{name}"

        filename = (
            "Contrib-"
            + "-".join(
                _FILENAME_MAP.get(part, part.capitalize() if part[0].islower() else part)
                for part in name.split("_")
            )
            + ".md"
        )
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

        with open(outfile, "w") as fil:
            fil.write(data)

        categories[category].append((name, credits, blurb, filename, pypath))
        ncount += 1

    # build the list of categories with blurbs

    category_sections = []
    for category in sorted(categories):
        filenames = []
        contrib_tups = categories[category]
        catlines = []
        for tup in sorted(contrib_tups, key=lambda tup: tup[0].lower()):
            catlines.append(
                BLURB.format(
                    name=tup[0], credits=tup[1], blurb=tup[2], filename=tup[3], code_location=tup[4]
                )
            )
            filenames.append(f"{tup[3]}")
        toctree = TOCTREE.format(listing="\n".join(filenames))
        category_sections.append(
            CATEGORY.format(
                category=category,
                category_desc=_CATEGORY_DESCS[category].strip(),
                blurbs="\n".join(catlines),
                toctree=toctree,
            )
        )

    # build the header, with two tables and a count
    header = HEADER.format(
        ncontribs=len(index),
        category_index=build_table(sorted(set(category_index)), 7),
        index=build_table(sorted(index), 5),
    )

    # build the final file

    text = _FILE_STRUCTURE.format(
        header=header, categories="\n".join(category_sections), footer=INDEX_FOOTER
    )

    with open(_OUT_INDEX_FILE, "w") as fil:
        fil.write(text)

    print(f"  -- Converted Contrib READMEs to {ncount} doc pages + index.")


if __name__ == "__main__":
    readmes2docs(_SOURCE_DIR)
