#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Prepare files for mkdoc. This assumes evennia.wiki is cloned
to a folder at the same level as the evennia-docs repo.

Just run this to update everything.

"""

import glob
import re

_RE_MD_LINK = re.compile(r"\[(?P<txt>[\w -]+)\]\((?P<url>\w+?)\)", re.I + re.S + re.U)

_WIKI_DIR = "../../evennia.wiki/"
_INFILES = sorted(glob.glob(_WIKI_DIR + "/*.md"))
_FILENAMES = [path.rsplit("/", 1)[-1] for path in _INFILES]
_FILENAMESLOW = [path.lower() for path in _FILENAMES]
_OUTDIR = "../sources/"

_CUSTOM_LINK_REMAP = {
    "CmdSets.md": "Command-Sets.md",
    "CmdSet.md": "Command-Sets.md",
    "Cmdsets.md": "Command-Sets.md",
    "CommandSet.md": "Command-Sets.md",
    "batch-code-processor.md": "Batch-Code-Processor.md",
    "Batch-code-processor.md": "Batch-Code-Processor.md",
    "batch-command-processor.md": "Batch-Command-Processor.md",
    "Batch-command-processor.md": "Batch-Command-Processor.md",
    "evennia-API.md": "Evennia-API.md",
    "Win.md": "Win",
    "Mac.md": "Mac",
    "IOS.md": "IOS",
    "Andr.md": "Andr",
    "Unix.md": "Unix",
    "Chrome.md": "Chrome",
    "EvTable.md": "EvTable.md",
    "Channels.md": "Communications.md#Channels",
    "Comms.md": "Communications.md",
    "typeclass.md": "Typeclasses.md",
    "Home.md": "index.md"
}


def _sub_link(match):
    mdict = match.groupdict()
    txt, url = mdict['txt'], mdict['url']
    if not txt:
        # the 'comment' is not supported by Mkdocs
        return ""
    url = url if url.endswith(".md") or url.startswith("http") else url + ".md"

    print("url:", url)
    url = _CUSTOM_LINK_REMAP.get(url, url)

    if url not in _FILENAMES and not url.startswith("http") and "#" not in url:
        url_cap = url.capitalize()
        url_plur = url[:-3] + 's' + ".md"
        url_cap_plur = url_plur.capitalize()

        print(f"Link [{txt}]({url}) has no matching target")
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
        inp = input("Enter alternate url (return to keep old): ")
        if inp.strip():
            url = inp.strip()

    return f"[{txt}]({url})"


for inpath in _INFILES:
    print(f"Converting links in {inpath} ->", end=" ")
    with open(inpath) as fil:
        text = fil.read()
        text = _RE_MD_LINK.sub(_sub_link, text)
        text = text.split('\n')[1:] if text.split('\n')[0].strip().startswith('[]') else text.split('\n')
        text = '\n'.join(text)

    outfile = inpath.rsplit('/', 1)[-1]
    if outfile == "Home.md":
        outfile = "index.md"
    outfile = _OUTDIR + outfile

    with open(outfile, 'w') as fil:
        fil.write(text)

    print(f"{outfile}.")
