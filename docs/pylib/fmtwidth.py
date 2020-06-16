#!/usr/bin python
# -*- coding: utf-8 -*-

"""
Format given files to a max width.

"""
import glob
import textwrap
import argparse

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("files")
    parser.add_argument("-w", '--width', dest="width", type=int, default=79)

    args = parser.parse_args()

    filepaths = glob.glob(args.files)

    wrapper = textwrap.TextWrapper(
        width=args.width,
        break_long_words=False,
        expand_tabs=True,
    )

    count = 0
    for filepath in filepaths:
        with open(filepath, 'r') as fil:
            txt = fil.read()
            txt = "\n".join(wrapper.wrap(txt))
        with open(filepath, 'w') as fil:
            fil.write(txt)
            count += 1

    print(f"Wrapped {count} files.")
