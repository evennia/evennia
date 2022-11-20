# Core Components

These are the 'building blocks' out of which Evennia is built. This documentation is complementary to, and often goes deeper than, the doc-strings of each component in the [API](../Evennia-API.md).

## Basic entites

These are base pieces used to make an Evennia game. Most are long-lived and are persisted in the database.

```{toctree} 
:maxdepth: 2

Typeclasses.md
Sessions.md
Accounts.md
Objects.md
Scripts.md
Channels.md
Msg.md
Attributes.md
Nicks.md
Tags.md
Prototypes.md
Help-System.md
Permissions.md
Portal-And-Server.md
```

## Commands

Evennia's Command system handle everything sent to the server by the user.

```{toctree} 
:maxdepth: 2

Command-System.md
Commands.md
Command-Sets.md
Default-Commands.md
Connection-Screen.md
Batch-Processors.md
Batch-Code-Processor.md
Batch-Command-Processor.md
Inputfuncs.md
Outputfuncs.md
```


## Utils and tools

Evennia provides a library of code resources to help the creation of a game.

```{toctree} 
:maxdepth: 2

Coding-Utils.md
EvEditor.md
EvForm.md
EvMenu.md
EvMore.md
EvTable.md
FuncParser.md
MonitorHandler.md
TickerHandler.md
Locks.md
Signals.md
```

## Web components

Evennia is also its own webserver, with a website and in-browser webclient you can expand on.

```{toctree} 
:maxdepth: 2

Website.md
Webclient.md
Web-Admin.md
Webserver.md
Web-API.md
Bootstrap-Components-and-Utilities.md
```