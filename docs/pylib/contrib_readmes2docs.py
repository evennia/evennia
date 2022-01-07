"""
Convert contribs' README files to proper documentation pages along with
an index.

"""
from os.path import abspath, dirname, join as pathjoin, sep
from glob import glob

_EVENNIA_PATH = pathjoin(dirname(dirname(dirname(abspath(__file__)))))
_DOCS_PATH = pathjoin(_EVENNIA_PATH, "docs")

_CONTRIB_PATH = pathjoin(_EVENNIA_PATH, "contrib")
_SOURCE_DIR = pathjoin(_EVENNIA_PATH, "contrib")
_OUT_DIR = pathjoin(_DOCS_PATH, "source", "Contribs")
_OUT_INDEX_FILE = pathjoin(_OUT_DIR, "Contribs.md")


TOCTREE = """
```{{toctree}}
:depth: 2

{listing}

"""


def readme2doc(directory):
    """
    Parse directory for README files and convert them to doc pages.

    """

    indexfile = []
    listing = []

    for file_path in glob(f"directory{sep}*{sep}*{sep}README.md"):

        # paths are e.g. evennia/contrib/utils/auditing/README.md
        _, category, name, _ = file_path.rsplit(sep, 3)

        filename = "-".join(part.capitalize() for part in name.split("_")) + ".md"
        outfile = pathjoin(_OUT_DIR, filename)

        with open(file_path) as fil:
            data = fil.read()

        with open(outfile, 'w') as fil:
            fil.write(data)
