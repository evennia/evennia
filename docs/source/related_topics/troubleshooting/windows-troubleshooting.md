```python
class Documentation:
    RATING = "Acceptable"
```

# Windows Troubleshooting
This is a Windows-specific version of the system-agnostic [troubleshooting](../../related_topics/troubleshooting/troubleshooting) guide.

## Installing Dependencies

## Installation
- Some Windows users get an error installing the Twisted 'wheel'. A wheel is a pre-compiled binary package for Python. A common reason for this error is that you are using a 32-bit version of Python, but Twisted has not yet uploaded the latest 32-bit wheel. Easiest way to fix this is to install a slightly older Twisted version. So if, say, version `18.1` failed, install `18.0` manually with `pip install twisted==18.0`. Alternatively you could try to get a 64-bit version of Python (uninstall the 32bit one). If so, you must then `deactivate` the virtualenv, delete the `evenv` folder and recreate it anew (it will then use the new Python executable).
- If your server won't start, with no error messages (and no log files at all when starting from scratch), try to start with `evennia ipstart` instead. If you then see an error about `system cannot find the path specified`, it may be that the file `evennia/evennia/server/twistd.bat` has the wrong path to the `twistd` executable. This file is auto-generated, so try to delete it and then run `evennia start` to rebuild it and see if it works. If it still doesn't work you need to open it in a text editor like Notepad. It's just one line containing  the path to the `twistd.exe` executable as determined by Evennia. If you installed Twisted in a non-standard location this might be wrong and you should update the line to the real location. 

