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

_RE_MD_LINK = re.compile(r"\[(?P<txt>[\w -]+)\]\((?P<url>.+?)\)", re.I + re.S + re.U)

_IGNORE_FILES = (
    "_Sidebar.md",
    # "Evennia-for-MUSH-Users.md",
    # "Installing-on-Android.md",
    # "Nicks.md",
    # "Spawner-and-Prototypes.md"
)

_WIKI_DIR = "../../../evennia.wiki/"
_INFILES = [path for path in sorted(glob.glob(_WIKI_DIR + "/*.md"))
            if path.rsplit('/', 1)[-1] not in _IGNORE_FILES]
_FILENAMES = [path.rsplit("/", 1)[-1] for path in _INFILES]
_FILENAMES = [path.split(".", 1)[0] for path in _FILENAMES]
_FILENAMESLOW = [path.lower() for path in _FILENAMES]
_OUTDIR = "../source/"
_OLD_WIKI_URL = "https://github.com/evennia/evennia/wiki/"
_OLD_WIKI_URL_LEN = len(_OLD_WIKI_URL)
_CODE_PREFIX = "code:"

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
    "Channels": "Communications#Channels",
    "Comms": "Communications",
    "typeclass": "Typeclasses",
    "Home": "index",
    "Help-system": "Help-System",
    "Using-Mux-as-a-Standard": "Using-MUX-as-a-Standard",
    "Building-quickstart": "Building-Quickstart",
    "Adding-Object-Typeclass-tutorial": "Adding-Object-Typeclass-Tutorial",
}

# absolute links (mainly github links) that should not be converted. This
# should be given without any #anchor.
_ABSOLUTE_LINK_SKIP = (
    "https://github.com/evennia/evennia/wiki/feature-request"
)

# specific references tokens that should be ignored. Should be given
# without any #anchor.
_REF_SKIP = (
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

    # "[Nicks](Nicks)",
    # "[Nick](Nicks)",
)


_CURRENT_TITLE = ""

def _sub_link(match):

    mdict = match.groupdict()
    txt, url_orig = mdict['txt'], mdict['url']
    url = url_orig
    # if not txt:
    #     # the 'comment' is not supported by Mkdocs
    #     return ""
    #  url = url if url.endswith(".md") or url.startswith("http") else url + ".md"

    url = _CUSTOM_LINK_REMAP.get(url, url)

    url, *anchor = url.rsplit("#", 1)

    if url in _ABSOLUTE_LINK_SKIP:
        url += (("#" + anchor[0]) if anchor else "")
        return f"[{txt}]({url})"

    if url.startswith(_OLD_WIKI_URL):
        # old wiki is an url on the form https://<wikiurl>/wiki/TextTags#header
        # we don't refer to the old wiki but use internal mapping.
        url_conv = url[_OLD_WIKI_URL_LEN:]
        url_conv = re.sub(r"%20", "-", url_conv)
        if url_conv.endswith("/_edit"):
            # this is actually a bug in the wiki format
            url_conv = url_conv[:-6]
        if url_conv.startswith("evennia"):
            # this is an api link
            url_conv = _CODE_PREFIX + url_conv

        print(f" Converting wiki-url: {url} -> {url_conv}")
        url = url_conv

    if not url and anchor:
        # this happens on same-file #labels in wiki
        url = _CURRENT_TITLE

    if (url not in _FILENAMES and
            not url.startswith("http") and not url.startswith(_CODE_PREFIX)):

        url_cap = url.capitalize()
        url_plur = url[:-3] + 's' + ".md"
        url_cap_plur = url_plur.capitalize()

        link = f"[{txt}]({url})"
        if link in _REF_SKIP:
            url = link
        elif url_cap in _FILENAMES:
            print(f" Replacing (capitalized): {url.capitalize()}")
            url = url_cap
        elif url_plur in _FILENAMES:
            print(f" Replacing (pluralized): {url + 's'}")
            url = url_plur
        elif url_cap_plur in _FILENAMES:
            print(f" Replacing (capitalized, pluralized): {url.capitalize() + 's'}")
            url = url_cap_plur
        elif url.lower() in _FILENAMESLOW:
            ind = _FILENAMESLOW.index(url.lower())
            alt = _FILENAMES[ind]
            print(f" Replacing {url} with different cap: {alt}")
            url = alt

            # print(f"\nlink {link} (orig: [{txt}]({url_orig})) found no file match")
            # inp = input("Enter alternate url (return to keep old): ")
            # if inp.strip():
            #     url = inp.strip()

    if anchor:
        url += "#" + anchor[0]

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
    global _CURRENT_TITLE

    print(_INFILES)

    for inpath in files:

        outfile = inpath.rsplit('/', 1)[-1]
        if outfile == "Home.md":
            outfile = "index.md"
        outfile = _OUTDIR + outfile

        title = inpath.rsplit("/", 1)[-1].split(".", 1)[0].replace("-", " ")

        print(f"Converting links in {inpath} -> {outfile} ...")
        with open(inpath) as fil:
            text = fil.read()
            _CURRENT_TITLE = title.replace(" ", "-")
            text = _RE_MD_LINK.sub(_sub_link, text)
            text = text.split('\n')[1:] if text.split('\n')[0].strip().startswith('[]') else text.split('\n')
            text = f"# {title}\n\n" + '\n'.join(text)

        with open(outfile, 'w') as fil:
            fil.write(text)

if __name__ == "__main__":

    create_toctree(_INFILES)
    convert_links(_INFILES, _OUTDIR)

