"""
Where discovery is allowed to look, and the refusal to look anywhere else.

THE RULE. Discovery reads Python source out of the *game directory* and nowhere
else. Not Evennia's own library, not site-packages, not a path a developer typed
on the command line, not wherever a symlink happens to point.

This is not about a hostile game author -- somebody who can edit the game
directory can already run anything. It is about two ordinary accidents:

- **A scan that wanders.** `world/` in a real game can contain a vendored
  library, a data dump, or a checkout of something else entirely. Walking
  everything under the game directory finds thousands of files, takes a long
  time, and reports candidates from code the developer does not own and cannot
  change.
- **A symlink out.** Developers symlink `world/` at a shared checkout more often
  than anyone expects. Following it silently means discovery reports on a
  different project's source and names it as the game's.

So the roots are named rather than discovered, and every file is resolved --
symlinks followed -- and checked to still be inside the game directory
afterwards. Resolving before the check rather than after is the whole point:
`os.path.join(gamedir, "world")` looks contained no matter where `world` leads.

WHY NOT `server/conf/settings.py`. It is the one file in a game directory that a
scan would obviously want, and it stays out. Reading it statically would tell
discovery what is already configured, which sounds useful and is the beginning
of a tool that edits it. Discovery prints a suggestion; comparing it with what is
already there is the developer's job, and they are looking right at it.

"""

import os

from django.conf import settings

from evennia.contrib.base_systems.aetos_webclient.discovery import redaction

#: Directories inside the game directory that discovery may read, relative to it.
#:
#: Named rather than walked. `typeclasses/` is where the Character lives and is
#: the only one that matters for D0; `world/` and `commands/` are here because
#: games routinely set attributes from both, and a candidate found in a command
#: is still a real candidate.
APPROVED_ROOTS = ("typeclasses", "world", "commands")

#: How deep to walk inside a root, counted in directories below it.
#:
#: 0 is `world/*.py`, 1 is `world/rules/*.py`, 2 is `world/rules/melee/*.py`, and
#: nothing below that is entered. A game's `world/` can contain a vendored
#: package tree, and this is where a scan stops being about the game and starts
#: being about its dependencies.
MAX_DEPTH = 2

#: Directory names never entered, at any depth.
#:
#: Not a security measure -- a scan that entered `.git` would read blobs and find
#: nothing. It is here so the scan stays fast and its output stays about the
#: game.
SKIP_DIRECTORIES = frozenset(
    {
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "migrations",
        "site-packages",
    }
)


#: The most files one run will read.
#:
#: Addendum B.56 asks for ceilings and, more importantly, for the scan to *say*
#: when it hits one. A game with more Python files than this has a vendored tree
#: in an approved root, and the report says how many were left.
MAX_FILES = 2000

#: The largest single file read, in bytes.
#:
#: A 512KB Python file is generated, minified or a data table. Parsing it costs
#: seconds and its candidates are not the ones anybody wanted.
MAX_FILE_BYTES = 512 * 1024

#: The most source read in one run, in bytes.
MAX_TOTAL_BYTES = 20 * 1024 * 1024


class ScanRootError(Exception):
    """
    Raised when discovery is asked to read outside the approved roots.

    Deliberately an exception rather than a skipped file. A path that escapes
    the game directory means an assumption is wrong somewhere, and continuing
    quietly would produce a report that names files the developer did not expect
    without saying so.

    """


def game_directory():
    """
    The game directory discovery is confined to.

    Returns:
        str: Absolute, resolved path to the game directory.

    Raises:
        ScanRootError: If Evennia has not set `GAME_DIR`, which means this is
            not running inside a game and there is nothing legitimate to scan.

    """
    gamedir = getattr(settings, "GAME_DIR", None)
    if not gamedir:
        raise ScanRootError(
            "settings.GAME_DIR is not set, so there is no game directory to scan. "
            "Run this from inside a game directory with `evennia aetos discover`."
        )
    return os.path.realpath(gamedir)


def is_inside(path, directory):
    """
    Whether a path is contained by a directory, after resolving both.

    Args:
        path (str): Path to test. Need not exist.
        directory (str): The containing directory.

    Returns:
        bool: True if `path` resolves to somewhere inside `directory`.

    Notes:
        `os.path.realpath` resolves symlinks, which is what makes this a
        containment check rather than a string comparison. `os.path.commonpath`
        rather than `startswith`, because `startswith` says
        `/game-backup` is inside `/game`.

    """
    resolved = os.path.realpath(path)
    directory = os.path.realpath(directory)
    if resolved == directory:
        return True
    try:
        return os.path.commonpath([resolved, directory]) == directory
    except ValueError:
        # Different drives on Windows. Not contained, and not an error worth
        # raising -- the answer to "is this inside" is simply no.
        return False


def approved_files(gamedir=None, roots=APPROVED_ROOTS):
    """
    Every Python file discovery is allowed to read, in a stable order.

    Args:
        gamedir (str, optional): The game directory. Defaults to
            `settings.GAME_DIR`.
        roots (tuple, optional): Root directory names, relative to the game
            directory. Defaults to `APPROVED_ROOTS`.

    Returns:
        list: Absolute paths to `.py` files, sorted.

    Raises:
        ScanRootError: If a root resolves outside the game directory.

    Notes:
        Sorted, because the report is something a developer reads twice and
        compares. A scan whose output reorders between runs for no reason costs
        more attention than the ordering saves.

    """
    gamedir = os.path.realpath(gamedir) if gamedir else game_directory()
    found = []

    for root in roots:
        start = os.path.join(gamedir, root)
        if not os.path.isdir(start):
            # A game without a `world/` is normal, not an error.
            continue
        if not is_inside(start, gamedir):
            raise ScanRootError(
                "%s resolves outside the game directory (%s). Discovery reads the "
                "game's own source and nothing else; if this is deliberate, copy "
                "the files in rather than linking to them." % (start, gamedir)
            )

        for current, directories, filenames in os.walk(start):
            directories[:] = sorted(d for d in directories if d not in SKIP_DIRECTORIES)

            # Counted in path components, not separators. Counting separators
            # made `world/a` depth 0 and every directory one shallower than it
            # claimed, so the walk went a level further than `MAX_DEPTH` says --
            # found by walking a four-deep tree and looking, not by reading it.
            relative = os.path.relpath(current, start)
            depth = 0 if relative == os.curdir else len(relative.split(os.sep))
            if depth >= MAX_DEPTH:
                directories[:] = []

            for filename in sorted(filenames):
                if not filename.endswith(".py"):
                    continue
                path = os.path.join(current, filename)
                # Checked per file, not per root: a single symlinked file inside
                # an ordinary directory is the case a per-root check misses.
                if not is_inside(path, gamedir):
                    continue
                found.append(path)

    return sorted(found)


def select_files(
    gamedir=None,
    roots=APPROVED_ROOTS,
    max_files=MAX_FILES,
    max_file_bytes=MAX_FILE_BYTES,
    max_total_bytes=MAX_TOTAL_BYTES,
):
    """
    The files to read, bounded, with a note about everything left out.

    Args:
        gamedir (str, optional): The game directory.
        roots (tuple, optional): Root directory names.
        max_files (int, optional): Ceiling on how many files are read.
        max_file_bytes (int, optional): Ceiling on one file's size.
        max_total_bytes (int, optional): Ceiling on the total read.

    Returns:
        tuple: `(paths, problems)`.

    Notes:
        **Nothing is left out silently** (B.56). A scan that quietly truncates
        teaches a developer that the attribute they were looking for does not
        exist, which is worse than a slow scan and much worse than an error.

        A source file whose *name* looks like it holds credentials is skipped
        unread. It is ordinary Python inside an approved root, so the walk would
        otherwise read `world/api_keys.py` and quote lines from it into a report
        somebody pastes into an issue. The name is the only warning available
        before reading, which is B.46's reasoning applied to a file.

    """
    paths = approved_files(gamedir, roots)
    base = os.path.realpath(gamedir) if gamedir else game_directory()
    chosen, problems = [], []
    sensitive, oversized = [], []
    total = 0
    stopped_at = None

    for index, path in enumerate(paths):
        # Named the way the report names everything else: relative to the
        # game directory, forward slashes. `huge.py` in a note is a file the
        # developer then has to go and find.
        name = os.path.relpath(path, base).replace(os.sep, "/")
        if redaction.is_sensitive(os.path.splitext(os.path.basename(path))[0]):
            sensitive.append(name)
            continue
        try:
            size = os.path.getsize(path)
        except OSError:  # pragma: no cover - defensive
            size = 0
        if size > max_file_bytes:
            oversized.append(name)
            continue
        if len(chosen) >= max_files or (chosen and total + size > max_total_bytes):
            stopped_at = index
            break
        chosen.append(path)
        total += size

    if stopped_at is not None:
        problems.append(
            "Discovery stopped after scanning %d files (%d KB). %d files were not "
            "scanned. Raise the ceiling in discovery/roots.py if that is wrong."
            % (len(chosen), total // 1024, len(paths) - stopped_at)
        )
    if oversized:
        problems.append(
            "Not read, larger than %d KB: %s"
            % (max_file_bytes // 1024, ", ".join(sorted(oversized)))
        )
    if sensitive:
        problems.append(
            "Not read, because the file name looks like it holds credentials: %s"
            % ", ".join(sorted(sensitive))
        )
    return chosen, problems
