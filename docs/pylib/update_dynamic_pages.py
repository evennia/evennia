"""
Update dynamically generated doc pages based on github sources.

"""

from os.path import dirname, abspath, join as pathjoin

ROOTDIR = dirname(dirname(dirname(abspath(__file__))))
DOCDIR = pathjoin(ROOTDIR, "docs")
DOCSRCDIR = pathjoin(DOCDIR, "source")
EVENNIADIR = pathjoin(ROOTDIR, "evennia")


def update_changelog():
    """
    Plain CHANGELOG copy

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


if __name__ == "__main__":
    update_dynamic_pages()
