"""
Project rename utility

Created for the Player->Account renaming

Griatch 2017, released under the BSD license.

"""


import re
import sys
import os
import fnmatch

ANSI_HILITE = "\033[1m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_NORMAL = "\033[0m"

USE_COLOR = True
FAKE_MODE = False

# if these words are longer than output word, retain given case
CASE_WORD_EXCEPTIONS = ('an', )

_HELP_TEXT = """This program interactively renames words in all files of your project. It's
currently renaming {sources} to {targets}.

If it wants to replace text in a file, it will show all lines (and line numbers) it wants to
replace, each directly followed by the suggested replacement.

If a rename is not okay, you can de-select it by entering 'i' followed by one or more
comma-separated line numbers. You cannot ignore partial lines, those you need to remember to change
manually later.

[q]uit - exits the program immediately.
[h]elp - this help.
[s]kip file - make no changes at all in this file, continue on to the next.
[i]ignore lines - specify line numbers to not change.
[c]lear ignores - this reverts all your ignores if you make a mistake.
[a]accept/save file - apply all accepted renames and continue on to the next file.

(return to continue)
"""

# Helper functions


def _green(string):
    if USE_COLOR:
        return "%s%s%s" % (ANSI_GREEN, string, ANSI_NORMAL)
    return string


def _yellow(string):
    if USE_COLOR:
        return "%s%s%s" % (ANSI_YELLOW, string, ANSI_NORMAL)
    return string


def _red(string):
    if USE_COLOR:
        return "%s%s%s" % (ANSI_HILITE + ANSI_RED, string, ANSI_NORMAL)
    return string


def _case_sensitive_replace(string, old, new):
    """
    Replace text, retaining exact case.

    Args:
        string (str): String in which to perform replacement.
        old (str): Word or substring to replace.
        new (str): What to replace `old` with.

    Returns:
        repl_string (str): Version of string where instances of
            `old` has been replaced with `new`, retaining case.

    """
    def repl(match):
        current = match.group()
        # treat multi-word sentences word-by-word
        old_words = current.split(" ")
        new_words = new.split(" ")
        out = []
        for old_word, new_word in zip(old_words, new_words):
            result = []
            all_upper = True
            for ind, chr in enumerate(old_word):
                if ind >= len(new_word):
                    break
                if chr.isupper():
                    result.append(new_word[ind].upper())
                else:
                    result.append(new_word[ind].lower())
                    all_upper = False
            # special cases - keep remaing case)
            if new_word.lower() in CASE_WORD_EXCEPTIONS:
                result.append(new_word[ind + 1:])
            # append any remaining characters from new
            elif all_upper:
                result.append(new_word[ind + 1:].upper())
            else:
                result.append(new_word[ind + 1:].lower())
            out.append("".join(result))
        # if we have more new words than old ones, just add them verbatim
        out.extend([new_word for ind, new_word in enumerate(new_words) if ind >= len(old_words)])
        return " ".join(out)

    regex = re.compile(re.escape(old), re.I)
    return regex.sub(repl, string)


def rename_in_tree(path, in_list, out_list, excl_list, fileend_list, is_interactive):
    """
    Rename across a recursive directory structure.

    Args:
        path (str): Root directory to traverse. All subdirectories
            will be visited.
        in_list (list): List of src words to replace.
        out_list (list): Matching list of words to replace with.
        excl_list (list): List of paths to exclude.
        fileend_list (list): List of file endings to accept. If
            not given, accept all file endings.
        is_interactive (bool): If we should stop to ask about the
            replacements in each file.

    """
    repl_mapping = list(zip(in_list, out_list))

    for root, dirs, files in os.walk(path):

        print("\ndir: %s\n" % root)

        if any(fnmatch.fnmatch(root, excl) for excl in excl_list):
            print("%s skipped (excluded)." % root)
            continue

        for file in files:

            full_path = os.path.join(root, file)
            if any(fnmatch.fnmatch(full_path, excl) for excl in excl_list):
                print("%s skipped (excluded)." % full_path)
                continue

            if not fileend_list or any(file.endswith(ending) for ending in fileend_list):
                rename_in_file(full_path, in_list, out_list, is_interactive)

            # rename file - always ask
            new_file = file
            for src, dst in repl_mapping:
                new_file = _case_sensitive_replace(new_file, src, dst)
            if new_file != file:
                inp = input(_green("Rename %s\n   ->  %s\n Y/[N]? > " % (file, new_file)))
                if inp.upper() == 'Y':
                    new_full_path = os.path.join(root, new_file)
                    try:
                        os.rename(full_path, new_full_path)
                    except OSError as err:
                        input(_red("Could not rename - %s (return to skip)" % err))
                    else:
                        print("... Renamed.")
                else:
                    print("... Skipped.")
        # rename the dir
        new_root = root
        for src, dst in repl_mapping:
            new_root = _case_sensitive_replace(new_root, src, dst)
        if new_root != root:
            inp = input(_green("Dir Rename %s\n       ->  %s\n Y/[N]? > " % (root, new_root)))
            if inp.upper() == 'Y':
                try:
                    os.rename(root, new_root)
                except OSError as err:
                    input(_red("Could not rename - %s (return to skip)" % err))
                else:
                    print("... Renamed.")
            else:
                print("... Skipped.")


def rename_in_file(path, in_list, out_list, is_interactive):
    """
    Args:
        path (str): Path to file in which to perform renaming.
        in_list (list): List of src words to replace.
        out_list (list): Matching list of words to replace with.
        is_interactive (bool): If we should stop to ask about the
            replacements in each file.

    """
    print("-- %s" % path)

    org_text = ""
    new_text = None
    if os.path.isdir(path):
        print("%s is a directory. You should use the --recursive option." % path)
        sys.exit()

    with open(path, 'r') as fil:
        org_text = fil.read()

    repl_mapping = list(zip(in_list, out_list))

    if not is_interactive:
        # just replace everything immediately
        new_text = org_text
        for src, dst in repl_mapping:
            new_text = _case_sensitive_replace(new_text, src, dst)
        if new_text != org_text:
            if FAKE_MODE:
                print("   ... Saved changes to %s. (faked)" % path)
            else:
                with open(path, 'w') as fil:
                    fil.write(new_text)
                print("   ... Saved changes to %s." % path)
    else:
        # interactive mode
        while True:
            renamed = {}

            org_lines = org_text.split("\n")

            for iline, old_line in enumerate(org_lines):
                new_line = old_line
                for src, dst in repl_mapping:
                    new_line = _case_sensitive_replace(new_line, src, dst)
                if new_line != old_line:
                    renamed[iline] = new_line

            if not renamed:
                # no changes
                print("   ... no changes to %s." % path)
                return

            while True:

                for iline, renamed_line in sorted(list(renamed.items()), key=lambda tup: tup[0]):
                    print("%3i orig: %s" % (iline + 1, org_lines[iline]))
                    print("    new : %s" % (_yellow(renamed_line)))
                print(_green("%s (%i lines changed)" % (path, len(renamed))))

                ret = input(_green("Choose: "
                                       "[q]uit, "
                                       "[h]elp, "
                                       "[s]kip file, "
                                       "[i]gnore lines, "
                                       "[c]lear ignores, "
                                       "[a]ccept/save file: ".lower()))

                if ret == "s":
                    # skip file entirely
                    print("   ... Skipping file %s." % path)
                    return
                elif ret == "c":
                    # clear ignores - rerun rename
                    break
                elif ret == "a":
                    # save result
                    for iline, renamed_line in renamed.items():
                        org_lines[iline] = renamed_line

                    if FAKE_MODE:
                        print("   ... Saved file %s (faked)" % path)
                        return
                    with open(path, 'w') as fil:
                        fil.writelines("\n".join(org_lines))
                    print("   ... Saved file %s" % path)
                    return
                elif ret == "q":
                    print("Quit renaming program.")
                    sys.exit()
                elif ret == "h":
                    input(_HELP_TEXT.format(sources=in_list, targets=out_list))
                elif ret.startswith("i"):
                    # ignore one or more lines
                    ignores = [int(ind) - 1 for ind in ret[1:].split(',') if ind.strip().isdigit()]
                    if not ignores:
                        input("Ignore example: i 2,7,34,133\n (return to continue)")
                        continue
                    for ign in ignores:
                        renamed.pop(ign, None)
                    continue


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Rename text in a source tree, or a single file")

    parser.add_argument('-i', '--input', action='append',
                        help="Source word to rename (quote around multiple words)")
    parser.add_argument('-o', '--output', action='append',
                        help="Word to rename a matching src-word to")
    parser.add_argument('-x', '--exc', action='append',
                        help="File path patterns to exclude")
    parser.add_argument('-a', '--auto', action='store_true',
                        help="Automatic mode, don't ask to rename")
    parser.add_argument('-r', '--recursive', action='store_true',
                        help="Recurse subdirs")
    parser.add_argument('-f', '--fileending', action='append',
                        help="Change which file endings to allow (default .py and .html)")
    parser.add_argument('--nocolor', action='store_true',
                        help="Turn off in-program color")
    parser.add_argument('--fake', action='store_true',
                        help="Simulate run but don't actually save")
    parser.add_argument('path',
                        help="File or directory in which to rename text")

    args = parser.parse_args()

    in_list, out_list, exc_list, fileend_list = args.input, args.output, args.exc, args.fileending

    if not (in_list and out_list):
        print('At least one source- and destination word must be given.')
        sys.exit()
    if len(in_list) != len(out_list):
        print('Number of sources must be identical to the number of destination arguments.')
        sys.exit()

    exc_list = exc_list or []
    fileend_list = fileend_list or [".py", ".html"]
    is_interactive = not args.auto
    is_recursive = args.recursive

    USE_COLOR = not args.nocolor
    FAKE_MODE = args.fake

    if is_recursive:
        rename_in_tree(args.path, in_list, out_list, exc_list, fileend_list, is_interactive)
    else:
        rename_in_file(args.path, in_list, out_list, is_interactive)
