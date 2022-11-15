#!/usr/bin python
# -*- coding: utf-8 -*-

"""
Format given files to a max width.

Usage:
    python fmtwidth.py --width 79 ../source/**.md

"""
import argparse
import glob
import textwrap

_DEFAULT_WIDTH = 100

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("files")
    parser.add_argument("-w", "--width", dest="width", type=int, default=_DEFAULT_WIDTH)

    args = parser.parse_args()

    filepaths = glob.glob(args.files, recursive=True)
    width = args.width

    wrapper = textwrap.TextWrapper(
        width=width,
        break_long_words=False,
        expand_tabs=True,
    )

    count = 0
    for filepath in filepaths:
        with open(filepath, "r") as fil:
            lines = fil.readlines()

            outlines = [
                "\n".join(wrapper.wrap(line)) if len(line) > width else line.strip("\n")
                for line in lines
            ]
            txt = "\n".join(outlines)
        with open(filepath, "w") as fil:
            fil.write(txt)
            count += 1

    print(f"Wrapped {count} files.")
