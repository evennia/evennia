"""
Do custom actions during build/install step.

"""

import os
import sys

from setuptools import setup

OS_WINDOWS = os.name == "nt"


def get_evennia_executable():
    """
    Called from build process.

    Determine which executable scripts should be added. For Windows,
    this means creating a .bat file.

    """
    if OS_WINDOWS:
        batpath = os.path.join("bin", "windows", "evennia.bat")
        scriptpath = os.path.join(sys.prefix, "Scripts", "evennia_launcher.py")
        with open(batpath, "w") as batfile:
            batfile.write('@"%s" "%s" %%*' % (sys.executable, scriptpath))
        return [batpath, os.path.join("bin", "windows", "evennia_launcher.py")]
    else:
        return [os.path.join("bin", "unix", "evennia")]


def get_all_files():
    """
    By default, the distribution tools ignore all non-python files, such as VERSION.txt.

    Make sure we get everything.
    """
    file_set = []
    for root, dirs, files in os.walk("evennia"):
        for f in files:
            if ".git" in f.split(os.path.normpath(os.path.join(root, f))):
                # Prevent the repo from being added.
                continue
            file_name = os.path.relpath(os.path.join(root, f), "evennia")
            file_set.append(file_name)
    return file_set


# legacy entrypoint
setup(scripts=get_evennia_executable(), package_data={"": get_all_files()})
