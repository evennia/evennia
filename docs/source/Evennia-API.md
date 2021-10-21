# API Summary

[evennia](api/evennia-api.md) - library source tree
- [evennia.accounts](evennia.accounts) - the out-of-character entities representing players
- [evennia.commands](evennia.commands) - handle all inputs. Also includes default commands
- [evennia.comms](evennia.comms) - in-game channels and messaging
- [evennia.contrib](evennia.contrib) - game-specific tools and code contributed by the community
- [evennia.help](evennia.help) - in-game help system
- [evennia.locks](evennia.locks) - limiting access to various systems and resources
- [evennia.objects](evennia.objects) - all in-game entities, like Rooms, Characters, Exits etc
- [evennia.prototypes](evennia.prototypes) - customize entities using dicts
- [evennia.scripts](evennia.scripts) - all out-of-character game objects
- [evennia.server](evennia.server) - core Server and Portal programs, also network protocols
- [evennia.typeclasses](evennia.typeclasses) - core database-python bridge
- [evennia.utils](evennia.utils) - lots of useful coding tools and utilities
- [evennia.web](evennia.web) - webclient, website and other web resources


## Shortcuts

Evennia's 'flat API' has shortcuts to common tools, available by only importing `evennia`.
The flat API is defined in `__init__.py` [viewable here](github:evennia/__init__.py)


### Main config

- [evennia.settings_default](github:evennia/settings_default.py) - all settings (modify/override in `mygame/server/settings.py`)

### Search functions

- [evennia.search_account](evennia.utils.search.search_account)
- [evennia.search_object](evennia.utils.search.search_object)
- [evennia.search_tag](evennia.utils.search.search_tag)
- [evennia.search_script](evennia.utils.search.search_script)
- [evennia.search_channel](evennia.utils.search.search_channel)
- [evennia.search_message](evennia.utils.search.search_message)
- [evennia.search_help](evennia.utils.search.search_help_entry)

### Create functions

- [evennia.create_account](evennia.utils.create.create_account)
- [evennia.create_object](evennia.utils.create.create_object)
- [evennia.create_script](evennia.utils.create.create_script)
- [evennia.create_channel](evennia.utils.create.create_channel)
- [evennia.create_help_entry](evennia.utils.create.create_help_entry)
- [evennia.create_message](evennia.utils.create.create_message)

### Typeclasses

- [evennia.Defaultaccount](evennia.accounts.accounts.DefaultAccount) - player account class ([docs](Components/Accounts.md))
- [evennia.DefaultGuest](evennia.accounts.accounts.DefaultGuest) - base guest account class
- [evennia.DefaultObject](evennia.objects.objects.DefaultObject) - base class for all objects ([docs](Components/Objects.md))
- [evennia.DefaultCharacter](evennia.objects.objects.DefaultCharacter) - base class for in-game characters ([docs](Components/Objects.md#characters))
- [evennia.DefaultRoom](evennia.objects.objects.DefaultRoom) - base class for rooms ([docs](Components/Objects.md#rooms))
- [evennia.DefaultExit](evennia.objects.objects.DefaultExit) - base class for exits ([docs](Components/Objects.md#exits))
- [evennia.DefaultScript](evennia.scripts.scripts.DefaultScript) - base class for OOC-objects ([docs](Components/Scripts.md))
- [evennia.DefaultChannel](evennia.comms.comms.DefaultChannel) - base class for in-game channels ([docs](Components/Channels.md))

### Commands

- [evennia.Command](evennia.commands.command.Command) - base [Command](Components/Commands.md) class. See also `evennia.default_cmds.MuxCommand`
- [evennia.CmdSet](evennia.commands.cmdset.CmdSet) - base [CmdSet](Components/Command-Sets.md) class
- [evennia.default_cmds](Components/Default-Commands.md) - access all default command classes as properties

- [evennia.syscmdkeys](Components/Commands.md#system-commands) - access system command keys as properties

### Utilities

- [evennia.utils.utils](evennia.utils.utils) - mixed useful utilities
- [evennia.gametime](evennia.utils.gametime.TimeScript) - server run- and game time ([docs](Components/Coding-Utils.md#game-time))
- [evennia.logger](evennia.utils.logger) - logging tools
- [evennia.ansi](evennia.utils.ansi) - ansi coloring tools
- [evennia.spawn](evennia.prototypes.spawner.spawn) - spawn/prototype system ([docs](Components/Prototypes.md))
- [evennia.lockfuncs](evennia.locks.lockfuncs) - default lock functions for access control ([docs](Components/Locks.md))
- [evennia.EvMenu](evennia.utils.evmenu.EvMenu) - menu system ([docs](Components/EvMenu.md))
- [evennia.EvTable](evennia.utils.evtable.EvTable) - text table creater
- [evennia.EvForm](evennia.utils.evform.EvForm) - text form creator
- Evennia.EvMore - text paginator
- [evennia.EvEditor](evennia.utils.eveditor.EvEditor) - in game text line editor ([docs](Components/EvEditor.md))
- [evennia.utils.funcparser.Funcparser](evennia.utils.funcparser.FuncParser) - inline parsing of functions ([docs](Components/FuncParser.md))

### Global singleton handlers

- [evennia.TICKER_HANDLER](evennia.scripts.tickerhandler.TickerHandler) - allow objects subscribe to tickers ([docs](Components/TickerHandler.md))
- [evennia.MONITOR_HANDLER](evennia.scripts.monitorhandler.MonitorHandler) - monitor changes ([docs](Components/MonitorHandler.md))
- [evennia.SESSION_HANDLER](evennia.server.sessionhandler.SessionHandler) - manages all sessionsmain session handler

### Database core models (for more advanced lookups)

- [evennia.ObjectDB](evennia.objects.models.ObjectDB)
- [evennia.accountDB](evennia.accounts.models.AccountDB)
- [evennia.ScriptDB](evennia.scripts.models.ScriptDB)
- [evennia.ChannelDB](evennia.comms.models.ChannelDB)
- [evennia.Msg](evennia.comms.models.Msg)
- evennia.managers - contains shortcuts to all database managers

### Contributions

- [evennia.contrib](https://github.com/evennia/evennia/blob/master/evennia/contrib/) -
game-specific contributions and plugins ([docs](https://github.com/evennia/evennia/blob/master/evennia/contrib/README.md))
