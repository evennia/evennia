"""
Build a TOC-tree; Sphinx requires it and this makes it easy to just
add/build/link new files without needing to explicitly add it to a toctree
directive somewhere.

"""

import re
from pathlib import Path
from os.path import abspath, dirname, join as pathjoin, sep

_IGNORE_FILES = []
_SOURCE_DIR = pathjoin(dirname(dirname(abspath(__file__))), "source")
_TOC_FILE = pathjoin(_SOURCE_DIR, "toc.md")


def create_toctree():
    """
    Create source/toc.md file
    """

    docref_map = {}

    for path in Path(_SOURCE_DIR).rglob("*.md"):
        # find the source/ part of the path and strip it out
        # support nesting of 3 within source/ dir
        fname = path.name
        if fname in _IGNORE_FILES:
            # this is the name including .md
            continue
        ind = path.parts[-4:].index("source")
        pathparts = path.parts[-4 + 1 + ind:]
        url = "/".join(pathparts)
        url = url.rsplit(".", 1)[0]
        fname = fname.rsplit(".", 1)[0]
        if fname in docref_map:
            raise RuntimeError(f"'{url}' and '{docref_map[fname]}': Auto-link correction does not "
                               "accept doc-files with the same name, even in different folders.")
        docref_map[fname] = url

    ref_regex = re.compile(r"\[(?P<txt>[\w -\[\]]+?)\]\((?P<url>"
                           + r"|".join(docref_map)
                           + r")\)", re.I + re.S + re.U)

    def _sub(match):
        grpdict = match.groupdict()
        txt, url = grpdict['txt'], grpdict['url']
        fname, *part = url.rsplit("/", 1)
        fname = part[0] if part else fname
        fname = fname.rsplit(".", 1)[0]
        urlout = docref_map.get(fname, url)
        if url != urlout:
            print(f"  Remapped link [{txt}]({url}) -> [{txt}]({urlout})")
        return f"[{txt}]({urlout})"

    # replace / correct links in all files
    count = 0
    for path in Path(_SOURCE_DIR).rglob("*.md"):
        with open(path, 'r') as fil:
            intxt = fil.read()
            outtxt = ref_regex.sub(_sub, intxt)
        if intxt != outtxt:
            with open(path, 'w') as fil:
                fil.write(outtxt)
            count += 1
            print(f"Auto-relinked links in {path.name}")

    if count > 0:
        print(f"Auto-corrected links in {count} documents.")

    # write tocfile
    with open(_TOC_FILE, "w") as fil:
        fil.write("# Toc\n")

        for ref  in sorted(docref_map.values()):

            if ref == "toc":
                continue

            linkname = ref.replace("-", " ")
            fil.write(f"\n- [{linkname}]({ref}.md)")

if __name__ == "__main__":
    create_toctree()
