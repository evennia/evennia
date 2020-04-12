```python
class Documentation:
    RATING = "Acceptable"
```

# Troubleshooting

## Installation
### Python won't start
`python --version` from a command line should return a supported version of Python. 
If it doesn't, you might try `python3 --version`. If neither of these commands work, 
your system cannot find the python executable. [Read more](https://wiki.python.org/moin/BeginnersGuide/Download)

To fix, run the correct Python executable with switches `-m virtualenv evenv`. You may have to explicitly point to your Python executable here, e.g.`C:\Program Files\Python\python.exe -m virtualenv evenv`  

### Missing dependencies
Read the 'Installing Dependencies' section on [Linux troubleshooting](../../related_topics/troubleshooting/linux-troubleshooting) or [Windows troubleshooting](../../related_topics/troubleshooting/windows-troubleshooting)

Evennia requires the following dependencies:
- [Python](http://www.python.org) (v3.7, 3.8 are tested)
  - [virtualenv](../../tutorials_and_examples/python/virtualenv) for making isolated
    Python environments.

- [GIT](http://git-scm.com/) - version control software for getting and
updating Evennia itself - Mac users can use the
[git-osx-installer](http://code.google.com/p/git-osx-installer/) or the
[MacPorts version](http://git-scm.com/book/en/Getting-Started-Installing-Git#Installing-on-Mac).
- [Twisted](http://twistedmatrix.com) (v19.0+)
  - [ZopeInterface](http://www.zope.org/Products/ZopeInterface) (v3.0+)  - usually included in Twisted packages
  - Linux/Mac users may need the `gcc` and `python-dev` packages or equivalent.
  - Windows users need [MS Visual C++](https://aka.ms/vs/16/release/vs_buildtools.exe) and *maybe* [pypiwin32](https://pypi.python.org/pypi/pypiwin32).
- [Django](http://www.djangoproject.com) (v2.2.x), be warned that latest dev
  version is usually untested with Evennia)

## Connecting
- [Making your game available online](../../related_topics/technical/online-setup)
- [Changing text encodings used by the server](../../evennia_core/system/portal/Text-Encodings)

### Localhost-related issues
Not all computers accept `localhost` as a valid IP address. Swap for `127.0.0.1` - this should always work.

