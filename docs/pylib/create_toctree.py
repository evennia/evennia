"""
Build a TOC-tree; Sphinx requires it and this makes it easy to just
add/build/link new files without needing to explicitly add it to a toctree
directive somewhere.

"""

import glob
from os.path import abspath, dirname, join as pathjoin, sep

_SOURCEDIR = "../source/"
_IGNORE_FILES = []
_SOURCE_DIR = pathjoin(dirname(dirname(abspath(__file__))), "source")
_TOC_FILE = pathjoin(_SOURCE_DIR, "toc.md")


def create_toctree():
    """
    Create source/toc.md file
    """
    _INFILES = [path for path in glob.glob(_SOURCE_DIR + sep + "*.md")
                if path.rsplit('/', 1)[-1] not in _IGNORE_FILES]
    # split out the name and remove the .md extension
    _FILENAMES = [path.rsplit("/", 1)[-1] for path in sorted(_INFILES)]
    _FILENAMES = [path.split(".", 1)[0] for path in _FILENAMES]

    with open(_TOC_FILE, "w") as fil:
        fil.write("# Toc\n")

        for ref in _FILENAMES:

            if ref == "toc":
                continue

            linkname = ref.replace("-", " ")
            fil.write(f"\n- [{linkname}]({ref}.md)")


if __name__ == "__main__":
    create_toctree()
