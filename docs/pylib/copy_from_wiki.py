#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copy data from old Evennia github Wiki to static files.

Prepare files for mkdoc. This assumes evennia.wiki is cloned
to a folder at the same level as the evennia repo.

Just run this to update everything.

We also need to build the toc-tree and should do so automatically for now.

"""

import glob
import re

_RE_MD_LINK = re.compile(r"\[(?P<txt>[\w -]+)\]\((?P<url>\w+?)\)", re.I + re.S + re.U)

_IGNORE_FILES = (
    "_Sidebar.md",
    "Evennia-for-MUSH-Users.md",
    "Installing-on-Android.md",
    "Nicks.md",
    "Spawner-and-Prototypes.md"
)

_WIKI_DIR = "../../../evennia.wiki/"
_INFILES = [path for path in sorted(glob.glob(_WIKI_DIR + "/*.md"))
            if path.rsplit('/', 1)[-1] not in _IGNORE_FILES]
_FILENAMES = [path.rsplit("/", 1)[-1] for path in _INFILES]
_FILENAMES = [path.split(".", 1)[0] for path in _FILENAMES]
_FILENAMESLOW = [path.lower() for path in _FILENAMES]
_OUTDIR = "../source/"

_CUSTOM_LINK_REMAP = {
    "CmdSets": "Command-Sets",
    "CmdSet": "Command-Sets",
    "Cmdsets": "Command-Sets",
    "CommandSet": "Command-Sets",
    "batch-code-processor": "Batch-Code-Processor",
    "Batch-code-processor": "Batch-Code-Processor",
    "batch-command-processor": "Batch-Command-Processor",
    "Batch-command-processor": "Batch-Command-Processor",
    "evennia-API": "Evennia-API",
    "Channels": "Communications.md#Channels",
    "Comms": "Communications",
    "typeclass": "Typeclasses",
    "Home": "index",

}

_LINK_SKIP = (
    "[5](Win)", "[6](Win)", "[7](Win)", "[10](Win)", "[11](Mac)", "[13](Win)",
    "[14](IOS)", "[15](IOS)", "[16](Andr)", "[17](Andr)", "[18](Unix)",
    "[21](Chrome)",
    # these should be checked
    "[EvTable](EvTable)",
    "[styled](OptionStyles)",
    "[Inputfunc](Inputfunc)",
    "[API](evennia)",
    "[online documentation wiki](index)",
    "[online documentation](index)",
    "[Home](index)",
    "[Accounts](Account)",
    "[Session](Session)",
    "[Inputfuncs](Inputfunc)",

    "[Nicks](Nicks)",
    "[Nick](Nicks)",
)


def _sub_link(match):
    mdict = match.groupdict()
    txt, url = mdict['txt'], mdict['url']
    # if not txt:
    #     # the 'comment' is not supported by Mkdocs
    #     return ""
    #  url = url if url.endswith(".md") or url.startswith("http") else url + ".md"

    url = _CUSTOM_LINK_REMAP.get(url, url)

    if url not in _FILENAMES and not url.startswith("http") and "#" not in url:
        url_cap = url.capitalize()
        url_plur = url[:-3] + 's' + ".md"
        url_cap_plur = url_plur.capitalize()

        link = f"[{txt}]({url})"
        if link in _LINK_SKIP:
            return link

        if url_cap in _FILENAMES:
            print(f" Replacing (capitalized): {url.capitalize()}")
            return url_cap
        if url_plur in _FILENAMES:
            print(f" Replacing (pluralized): {url + 's'}")
            return url_plur
        if url_cap_plur in _FILENAMES:
            print(f" Replacing (capitalized, pluralized): {url.capitalize() + 's'}")
            return url_cap_plur
        if url.lower() in _FILENAMESLOW:
            ind = _FILENAMESLOW.index(url.lower())
            alt = _FILENAMES[ind]
            print(f" Possible match (different cap): {alt}")
        print(f"\nlink {link} found no file match")
        inp = input("Enter alternate url (return to keep old): ")
        if inp.strip():
            url = inp.strip()

    return f"[{txt}]({url})"

def create_toctree(files):

    with open("../source/toc.md", "w") as fil:
        fil.write("# Toc\n")

        for path in files:
            filename = path.rsplit("/", 1)[-1]
            ref = filename.rsplit(".", 1)[0]
            linkname = ref.replace("-", " ")

            fil.write(f"\n* [{linkname}]({ref}.md)")

def convert_links(files, outdir):

    for inpath in files:

        title = inpath.rsplit("/", 1)[-1].split(".", 1)[0].replace("-", " ")

        print(f"Converting links in {inpath} ->", end=" ")
        with open(inpath) as fil:
            text = fil.read()
            text = _RE_MD_LINK.sub(_sub_link, text)
            text = text.split('\n')[1:] if text.split('\n')[0].strip().startswith('[]') else text.split('\n')
            text = f"# {title}\n\n" + '\n'.join(text)

        outfile = inpath.rsplit('/', 1)[-1]
        if outfile == "Home.md":
            outfile = "index.md"
        outfile = _OUTDIR + outfile

        with open(outfile, 'w') as fil:
            fil.write(text)

        print(f"{outfile}.")


if __name__ == "__main__":

    create_toctree(_INFILES)
    convert_links(_INFILES, _OUTDIR)

