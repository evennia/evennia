# DebugPy VSCode debugger integration

Contribution by electroglyph, 2025

This registers an in-game command `debugpy` which starts the debugpy debugger and listens on port 5678.
For now this is only available for Visual Studio Code (VS Code).

If you are a JetBrains PyCharm user and would like to use this, make some noise at:
https://youtrack.jetbrains.com/issue/PY-63403/Support-debugpy


Credit for this goes to Moony on the Evennia Discord getting-help channel, thx Moony!


## Installation

This requires VS Code and debugpy, so make sure you're using VS Code.

From the venv where you installed Evennia run:

`pip install debugpy`

### Enable the command in Evennia

In your Evennia mygame folder, open up `/commands/default_cmdsets.py`

add `from evennia.contrib.utils.debugpy import CmdDebugPy` somewhere near the top.

in `CharacterCmdSet.at_cmdset_creation` add this under `super().at_cmdset_creation()`:

`self.add(CmdDebugPy)`


### Add "remote attach" option to VS Code debugger

Start VS Code and open your launch.json like this:

![screenshot](./vscode.png)

Add this to your configuration:

```json
        {
            "name": "Python Debugger: Remote Attach",
            "justMyCode": false,
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "127.0.0.1",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "${workspaceFolder}"
                }
            ]
        },
```

Use `127.0.0.1` for the host if you are running Evennia from the same machine you'll be debugging from.  Otherwise, if you want to debug a remote server, change host (and possibly remoteRoot mapping) as necessary.

Afterwards it should look something like this:

```json
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python Debugger: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
        },
        {
            "name": "Python Debugger: Remote Attach",
            "justMyCode": false,
            "type": "debugpy",
            "request": "attach",
            "connect": {
                "host": "127.0.0.1",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "${workspaceFolder}"
                }
            ]
        },
    ]
}
```

(notice the comma between the curly braces)

## Usage

Set a breakpoint in VS Code where you want the debugger to stop at.

In Evennia run `debugpy` command.

You should see "Waiting for debugger attach..."

Back in VS Code attach the debugger:

![screenshot](./attach.png)

Back in Evennia you should see "Debugger attached."

Now trigger the breakpoint you set and you'll be using a nice graphical debugger.
