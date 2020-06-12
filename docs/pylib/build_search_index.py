#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Builds a lunr static search index for optimized search

"""
import os
import json
import glob
from argparse import ArgumentParser
from os.path import sep, abspath, dirname, join as joinpath
from lunr import lunr

_DOCS_PATH = dirname(dirname(abspath(__file__)))

_DEFAULT_BUILD_DIR = joinpath(_DOCS_PATH, "build", "html")
_DEFAULT_URL_BASE = f"file://{_DEFAULT_BUILD_DIR}"
_INDEX_PATH = joinpath("_static", "js", "lunr", "search_index.json")

DEFAULT_SOURCE_DIR = joinpath(_DOCS_PATH, "source")
DEFAULT_OUTFILE = joinpath(DEFAULT_SOURCE_DIR, _INDEX_PATH)

URL_BASE = os.environ.get("SEARCH_URL_BASE", _DEFAULT_URL_BASE)


def create_search_index(sourcedir, outfile):
    """
    Create the index.

    Args:
        sourcedir (str): Path to the source directory. This will be searched
            for both .md and .rst files.
        outfile (str): Path to the index file to create.

    """
    markdown_files = glob.glob(f"{sourcedir}{sep}*.md")
    markdown_files.extend(glob.glob(f"{sourcedir}{sep}*{sep}*.md"))
    rest_files = glob.glob(f"{sourcedir}{sep}*.rst")
    rest_files.extend(glob.glob(f"{sourcedir}{sep}*{sep}*.rst"))
    filepaths = markdown_files + rest_files

    outlist = []

    print(f"Building Search index from {len(filepaths)} files ... ", end="")

    for filepath in filepaths:
        with open(filepath, 'r') as fil:
            filename = filepath.rsplit(sep, 1)[1].split(".", 1)[0]
            url = f"{URL_BASE}{sep}{filename}.html".strip()
            title = filename.replace("-", " ").strip()
            body = fil.read()

            data = {
                "url": url,
                "title": title,
                "text": body,
            }
            outlist.append(data)

    idx = lunr(
        ref="url",
        documents=outlist,
        fields=[
            {
                "field_name": "title",
                "boost": 10
            },
            {
                "field_name": "text",
                "boost": 1
            }
        ],
    )

    with open(outfile, "w") as fil:
        fil.write(json.dumps(idx.serialize()))

    print(f"wrote to source{sep}{_INDEX_PATH}.")


if __name__ == "__main__":

    parser = ArgumentParser(description="Build a static search index.")

    parser.add_argument("-i", dest="sourcedir", default=DEFAULT_SOURCE_DIR,
                        help="Absolute path to the documentation source dir")
    parser.add_argument("-o", dest="outfile", default=DEFAULT_OUTFILE,
                        help="Absolute path to the index file to output.")

    args = parser.parse_args()

    create_search_index(args.sourcedir, args.outfile)
