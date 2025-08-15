
# Evennia Server Lifecycle

As part of your game design you may want to change how Evennia behaves when starting or stopping. A common use case would be to start up some piece of custom code you want to always have available once the server is up. 

Evennia has three main life cycles, all of which you can add custom behavior for:

- **Database life cycle**: Evennia uses a database. This exists in parallel to the code changes you do. The database exists until you choose to reset or delete it. Doing so doesn't require re-downloading Evennia.
- **Reboot life cycle**: From When Evennia starts to it being fully shut down, which means both Portal and Server are stopped. At the end of this cycle, all players are disconnected.
- **Reload life cycle:** This is the main runtime, until a "reload" event. Reloads refreshes game code but do not kick any players.

## When Evennia starts for the first time

This is the beginning of the **Database life cycle**, just after the database is created and migrated for the first time (or after it was deleted and re-built). See [Choosing a Database](../Setup/Choosing-a-Database.md) for instructions on how to reset a database, should you want to re-run this sequence after the first time.

Hooks called, in sequence: 

1.  `evennia.server.initial_setup.handle_setup(last_step=None)`: Evennia's core initialization function. This is what creates the #1 Character (tied to the superuser account) and `Limbo` room. It calls the next hook below and also understands to restart at the last failed step if there was some issue. You should normally not override this function unless you _really_ know what you are doing. To override, change `settings.INITIAL_SETUP_MODULE` to your own module with a `handle_setup` function in it.
2. `mygame/server/conf/at_initial_setup.py` contains a single function, `at_initial_setup()`, which will be called without arguments. It's called last in the setup sequence by the above function. Use this to add your own custom behavior or to tweak the initialization. If you for example wanted to change the auto-generated Limbo room, you should do it from here. If you want to change where this function is found, you can do so by changing `settings.AT_INITIAL_SETUP_HOOK_MODULE`. 

## When Evennia starts and shutdowns 

This is part of the **Reboot life cycle**. Evennia consists of two main processes, the [Portal and the Server](../Components/Portal-And-Server.md). On a reboot or shutdown, both Portal and Server shuts down, which means all players are disconnected. 

Each process call a series of hooks located in `mygame/server/conf/at_server_startstop.py`. You can customize the module used with `settings.AT_SERVER_STARTSTOP_MODULE` - this can even be a list of modules, if so, the appropriately-named functions will be called from each module, in sequence. 

All hooks are called without arguments. 

> The use of the term 'server' in the hook-names indicate the whole of Evennia, not just the `Server` component.

### Server cold start 

Starting the server from zero, after a full stop. This is done with `evennia start` from the terminal.

1. `at_server_init()` - Always called first in the startup sequence.
2. `at_server_cold_start()` - Only called on cold starts.
3. `at_server_start()` - Always called last in the startup sequece. 

### Server cold shutdown

Shutting everything down. Done with `shutdown` in-game or `evennia stop` from the terminal.

1. `at_server_cold_stop()` - Only called on cold stops.
2. `at_server_stop()` - Always called last in the stopping sequence.

### Server reboots 

This is done with `evennia reboot` and effectively constitutes an automatic cold shutdown followed by a cold start controlled from the `evennia` launcher. There are no special `reboot` hooks for this, instead it looks like you'd expect:

1. `at_server_cold_stop()`
2. `at_server_stop()`  (after this, both `Server` + `Portal` have both shut down)
3. `at_server_init()`  (like a cold start)
4. `at_server_cold_start()`
5. `at_server_start()`

## When Evennia reloads and resets

This is the **Reload life cycle**. As mentioned above, Evennia consists of two components, the [Portal and Server](../Components/Portal-And-Server.md). During a reload, only the `Server` component is shut down and restarted. Since the Portal stays up, players are not disconnected.

All hooks are called without arguments. 

### Server reload

Reloads are initiated with the `reload` command in-game, or with `evennia reload` from the terminal.

1. `at_server_reload_stop()` - Only called on reload stops.
2. `at_server_stop` - Always called last in the stopping sequence.
3. `at_server_init()` - Always called first in startup sequence.
4. `at_server_reload_start()` - Only called on a reload (re)start.
5. `at_server_start()` - Always called last in the startup sequence. 

### Server reset

A 'reset' is a hybrid reload state, where the reload is treated as a cold shutdown only for the sake of running hooks (players are not disconnected). It's run with `reset` in-game or with `evennia reset` from the terminal. 

1. `at_server_cold_stop()`
2. `at_server_stop()`  (after this, only `Server` has shut down)
3. `at_server_init()`  (`Server` coming back up)
4. `at_server_cold_start()`
5. `at_server_start()`
