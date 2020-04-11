```python
class Documentation:
    RATING = "Acceptable"
```

# Linux Troubleshooting
This is a linux-specific version of the system-agnostic [troubleshooting](related_topics/troubleshooting) guide.

## Installing Dependencies
```
sudo apt-get update
sudo apt-get install python3 python3-pip python3-dev python3-setuptools python3-git python3-virtualenv gcc

# If you are using an Ubuntu version that defaults to Python3, like 18.04+, use this instead:
sudo apt-get update
sudo apt-get install python3.7 python3-pip python3.7-dev python3-setuptools virtualenv gcc
``` 

After installing dependencies, run `pip install -e evennia` again and continue

## Installation
- One user reported a rare issue on Ubuntu 16 is an install error on installing Twisted; `Command "python setup.py egg_info" failed with error code 1 in /tmp/pip-build-vnIFTg/twisted/` with errors like `distutils.errors.DistutilsError: Could not find suitable distribution for Requirement.parse('incremental>=16.10.1')`. This appears possible to solve by simply updating Ubuntu with `sudo apt-get update && sudo apt-get dist-upgrade`.
- Users of Fedora (notably Fedora 24) has reported a `gcc` error saying the directory `/usr/lib/rpm/redhat/redhat-hardened-cc1` is missing, despite `gcc` itself being installed. [The confirmed work-around](https://gist.github.com/yograterol/99c8e123afecc828cb8c) seems to be to install the `redhat-rpm-config` package with e.g. `sudo dnf install redhat-rpm-config`.
- Some users trying to set up a virtualenv on an NTFS filesystem find that it fails due to issues with symlinks not being supported. 

