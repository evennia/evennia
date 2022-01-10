"""
Build a TOC-tree; Sphinx requires it and this makes it easy to just
add/build/link new files without needing to explicitly add it to a toctree
directive somewhere.

"""

import re
from collections import defaultdict
from sphinx.errors import DocumentError
from pathlib import Path
from os.path import abspath, dirname, join as pathjoin, relpath

_IGNORE_FILES = []
_SOURCEDIR_NAME = "source"
_SOURCE_DIR = pathjoin(dirname(dirname(abspath(__file__))), _SOURCEDIR_NAME)
_TOC_FILE = pathjoin(_SOURCE_DIR, "toc.md")
_NO_REMAP_STARTSWITH = [
    "http://",
    "https://",
    "github:",
    "feature-request",
    "report-bug",
    "issue",
    "bug-report",
]
# remove these prefixes from the url
_STRIP_PREFIX = [
    "../../api/",
    "../api/",
    "./api/",
    "api/",
    "api:",
]
TXT_REMAPS = {
    "Developer Central": "Evennia Components overview",
    "Getting Started": "Setup Quickstart",
}
URL_REMAPS = {
    "Developer-Central": "Components/Components-Overview",
    "Tutorials": "Howto/Howto-Overview",
    "../Howto/Starting/Directory-Overview": "Gamedir-Overview",
    "Howto/Starting/Directory-Overview": "Gamedir-Overview",
    "Starting/Directory-Overview": "Gamedir-Overview",
    "Directory-Overview": "Gamedir-Overview",
    "../Setup/Getting-Started": "Setup-Quickstart",
    "Setup/Getting-Started": "Setup-Quickstart",
    "Getting-Started": "Setup-Quickstart",
    "First-Steps-Coding": "Starting-Part1",
    "../Howto/Starting/Adding-Command-Tutorial": "Adding-Commands",
    "Howto/Starting/Adding-Command-Tutorial": "Adding-Commands",
    "Starting/Adding-Command-Tutorial": "Adding-Commands",
    "Adding-Command-Tutorial": "Adding-Commands",
    "CmdSet": "Command-Sets",
    "Spawner": "Prototypes",
    "issue": "github:issue",
    "issues": "github:issue",
    "bug": "github:issue",
    "bug-report": "github:issue",
    "./Default-Command-Help": "api:evennia.commands.default#modules",
    "../Components/Default-Command-Help": "api:evennia.commands.default#modules",
    "../../../Components/Default-Command-Help": "api:evennia.commands.default#modules",
    "./Locks.md#permissions": "Permissions",
    "modules": "Default-Commands.md",
}

_USED_REFS = {}

_CURRFILE = None


def auto_link_remapper(no_autodoc=False):
    """
    - Auto-Remaps links to fit with the actual document file structure. Requires
      all doc files to have a unique name.
    - Creates source/toc.md file

    """
    global _CURRFILE

    print("  -- Auto-Remapper starting.")

    def _get_rel_source_ref(path):
        """Get the path relative the source/ dir"""
        pathparts = path.split("/")
        # we allow a max of 4 levels of nesting in the source dir
        ind = pathparts[-5:].index(_SOURCEDIR_NAME)
        # get the part after source/
        pathparts = pathparts[-5 + 1 + ind :]
        url = "/".join(pathparts)
        # get the reference, without .md
        url = url.rsplit(".", 1)[0]
        return url

    toc_map = {}
    docref_map = defaultdict(dict)

    for path in Path(_SOURCE_DIR).rglob("*.md"):
        # find the source/ part of the path and strip it out

        if path.name in _IGNORE_FILES:
            # this is the name including .md
            continue

        sourcepath = path.as_posix()
        # get name and url relative to source/
        fname = path.name.rsplit(".", 1)[0]
        src_url = _get_rel_source_ref(sourcepath)

        # check for duplicate files
        if fname in toc_map:
            duplicate_src_url = toc_map[fname]
            raise DocumentError(
                f" Tried to add {src_url}.md, but a file {duplicate_src_url}.md already exists.\n"
                " Evennia's auto-link-corrector does not accept doc-files with the same \n"
                " name, even in different folders. Rename one.\n"
            )
        toc_map[fname] = src_url

        # find relative links to all other files
        for targetpath in Path(_SOURCE_DIR).rglob("*.md"):

            targetname = targetpath.name.rsplit(".", 1)[0]
            targetpath = targetpath.as_posix()
            url = relpath(targetpath, dirname(sourcepath))
            if not "/" in url:
                # need to be explicit or there will be link ref collisions between
                # e.g. TickerHandler page and TickerHandle api node
                url = "./" + url
            docref_map[sourcepath][targetname] = url.rsplit(".", 1)[0]

    # normal reference-links [txt](urls)
    ref_regex = re.compile(
        r"\[(?P<txt>[\n\w -\[\]\`]+?)\]\((?P<url>.+?)\)", re.I + re.S + re.U + re.M
    )
    # in document references
    ref_doc_regex = re.compile(
        r"\[(?P<txt>[\n\w -\`]+?)\]:\s+?(?P<url>.+?)(?=$|\n)", re.I + re.S + re.U + re.M
    )

    def _sub(match):
        # inline reference links
        global _USED_REFS
        grpdict = match.groupdict()
        txt, url = grpdict["txt"], grpdict["url"]

        txt = TXT_REMAPS.get(txt, txt)
        url = URL_REMAPS.get(url, url)

        for strip_prefix in _STRIP_PREFIX:
            if url.startswith(strip_prefix):
                url = url[len(strip_prefix):]

        if any(url.startswith(noremap) for noremap in _NO_REMAP_STARTSWITH):
            # skip regular http/s urls etc
            return f"[{txt}]({url})"

        if url.startswith("evennia."):
            # api link - we want to remove legacy #reference and remove .md
            if '#' in url:
                _, url = url.rsplit('#', 1)
            if url.endswith(".md"):
                url, _ = url.rsplit('.', 1)
            return f"[{txt}]({url})"

        fname, *part = url.rsplit("/", 1)
        fname = part[0] if part else fname
        fname, *anchor = fname.rsplit("#", 1)
        if ".md" in fname:
            fname = fname.rsplit(".", 1)[0]

        if not _CURRFILE.endswith("toc.md"):
            _USED_REFS[fname] = url

        if _CURRFILE in docref_map and fname in docref_map[_CURRFILE]:
            cfilename = _CURRFILE.rsplit("/", 1)[-1]
            urlout = docref_map[_CURRFILE][fname] + ".md" + ("#" + anchor[0].lower() if anchor else "")
            if urlout != url:
                print(f"  {cfilename}: [{txt}]({url}) -> [{txt}]({urlout})")
        else:
            urlout = url

        return f"[{txt}]({urlout})"

    def _sub_doc(match):
        # reference links set at the bottom of the page
        global _USED_REFS
        grpdict = match.groupdict()
        txt, url = grpdict["txt"], grpdict["url"]

        txt = TXT_REMAPS.get(txt, txt)
        url = URL_REMAPS.get(url, url)

        for strip_prefix in _STRIP_PREFIX:
            if url.startswith(strip_prefix):
                url = url[len(strip_prefix):]

        if any(url.startswith(noremap) for noremap in _NO_REMAP_STARTSWITH):
            return f"[{txt}]: {url}"

        if "http" in url and "://" in url:
            urlout = url
        elif url.startswith("evennia."):
            # api link - we want to remove legacy #reference
            if '#' in url:
                _, urlout = url.rsplit('#', 1)
        else:
            fname, *part = url.rsplit("/", 1)
            fname = part[0] if part else fname
            fname = fname.rsplit(".", 1)[0]
            fname, *anchor = fname.rsplit("#", 1)

            if not _CURRFILE.endswith("toc.md"):
                _USED_REFS[fname] = url

            if _CURRFILE in docref_map and fname in docref_map[_CURRFILE]:
                cfilename = _CURRFILE.rsplit("/", 1)[-1]
                urlout = docref_map[_CURRFILE][fname] + ("#" + anchor[0] if anchor else "")
                if urlout != url:
                    print(f"  {cfilename}: [{txt}]: {url} -> [{txt}]: {urlout}")
            else:
                urlout = url

        return f"[{txt}]: {urlout}"

    # replace / correct links in all files
    count = 0
    for path in sorted(Path(_SOURCE_DIR).rglob("*.md"), key=lambda p: p.name):

        # from pudb import debugger;debugger.Debugger().set_trace()
        _CURRFILE = path.as_posix()

        with open(path, "r") as fil:
            intxt = fil.read()
            outtxt = ref_regex.sub(_sub, intxt)
            outtxt = ref_doc_regex.sub(_sub_doc, outtxt)
        if intxt != outtxt:
            with open(path, "w") as fil:
                fil.write(outtxt)
            count += 1
            print(f"  -- Auto-relinked links in {path.name}")

    if count > 0:
        print(f"  -- Auto-corrected links in {count} documents.")

    for (fname, src_url) in sorted(toc_map.items(), key=lambda tup: tup[0]):
        if fname not in _USED_REFS and not src_url.startswith("api/"):
            print(f"  ORPHANED DOC: no refs found to {src_url}.md")

    # write tocfile
    with open(_TOC_FILE, "w") as fil:
        fil.write("```{toctree}\n")

        if not no_autodoc:
            fil.write("- [API root](api/evennia-api.rst)")

        for ref in sorted(toc_map.values()):

            if ref == "toc":
                continue

            # if not "/" in ref:
            #     ref = "./" + ref

            # linkname = ref.replace("-", " ")
            fil.write(f"\n{ref}")  # - [{linkname}]({ref})")

        # we add a self-reference so the toc itself is also a part of a toctree
        fil.write("\n```\n\n```{toctree}\n  :hidden:\n\ntoc\n```")
        print("  -- File toc.md updated.")

    print("  -- Auto-Remapper finished.")


if __name__ == "__main__":
    auto_link_remapper()
