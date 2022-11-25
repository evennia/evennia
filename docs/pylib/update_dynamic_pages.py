"""
Update dynamically generated doc pages based on github sources.

"""

from os.path import abspath, dirname
from os.path import join as pathjoin

ROOTDIR = dirname(dirname(dirname(abspath(__file__))))
DOCDIR = pathjoin(ROOTDIR, "docs")
DOCSRCDIR = pathjoin(DOCDIR, "source")
EVENNIADIR = pathjoin(ROOTDIR, "evennia")


def update_code_style():
    """
    Plain CODING_STYLE.md copy

    """
    sourcefile = pathjoin(ROOTDIR, "CODING_STYLE.md")
    targetfile = pathjoin(DOCSRCDIR, "Coding", "Evennia-Code-Style.md")

    with open(sourcefile) as fil:
        txt = fil.read()

    with open(targetfile, "w") as fil:
        fil.write(txt)

    print("  -- Updated Evennia-Code-Style.md")


def update_changelog():
    """
    Plain CHANGELOG.md copy

    """

    sourcefile = pathjoin(ROOTDIR, "CHANGELOG.md")
    targetfile = pathjoin(DOCSRCDIR, "Coding", "Changelog.md")

    with open(sourcefile) as fil:
        txt = fil.read()

    with open(targetfile, "w") as fil:
        fil.write(txt)

    print("  -- Updated Changelog.md")


def update_default_settings():
    """
    Make a copy of the default settings file for easy reference in docs

    """

    sourcefile = pathjoin(EVENNIADIR, "settings_default.py")
    targetfile = pathjoin(DOCSRCDIR, "Setup", "Settings-Default.md")

    with open(sourcefile) as fil:
        txt = fil.read()

    txt = f"""
# Evennia Default settings file

Master file is located at `evennia/evennia/settings_default.py`. Read
its comments to see what each setting does and copy only what you want
to change into `mygame/server/conf/settings.py`.

Example of accessing settings:

```
from django.conf import settings

if settings.SERVERNAME == "Evennia":
    print("Yay!")
```

----

```python
{txt}
```
"""
    with open(targetfile, "w") as fil:
        fil.write(txt)

    print("  -- Updated Settings-Default.md")


def update_dynamic_pages():
    """
    Run the various updaters

    """
    update_changelog()
    update_default_settings()
    update_code_style()


if __name__ == "__main__":
    update_dynamic_pages()
