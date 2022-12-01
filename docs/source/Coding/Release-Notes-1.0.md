# Evennia 1.0 Release Notes 

This summarizes the changes. See the [Changelog](./Changelog.md) for the full list.

## Minimum requirements

- Python 3.10 is now required minimum. Ubuntu LTS now installs with 3.10. Evennia 1.0 is also tested with Python 3.11 - this is the recommended version for Linux/Mac. Windows users may want to stay on Python 3.10 unless they are okay with installing a C++ compiler. 
- Twisted 22.10+
- Django 4.1+

## Major new features

- Evennia is now on PyPi and is installable as [pip install evennia](../Setup/Installation.md). 
- A completely revamped documentation at https://www.evennia.com/docs/latest. The old wiki and readmedocs pages will close.
-  Evennia 1.0 now has a REST API which allows you access game objects using CRUD operations GET/POST etc. See [The Web-API docs][Web-API] for more information.
- [Evennia<>Discord Integration](../Setup/Channels-to-Discord.md) between Evennia channels and Discord servers.
- [Script](../Components/Scripts.md) overhaul: Scripts' timer component independent from script object deletion; can now start/stop  timer without deleting Script. The `.persistent` flag now only controls if timer survives reload - Script has to be removed with `.delete()` like other typeclassed entities. This makes Scripts even more useful as general storage entities.
- The [FuncParser](../Components/FuncParser.md) centralizes and vastly improves all in-string function calls, such as `say the result is $eval(3 * 7)` and say the result `the result is 21`. The parser completely replaces the old `parse_inlinefunc`. The new parser can handle both arguments and kwargs and are also used for in-prototype parsing as well as director stance messaging, such as using `$You()` to represent yourself in a string and having the result come out differently depending on who see you.
- [Channels](../Components/Channels.md) New Channel-System using the `channel` command and nicks. The old `ChannelHandler` was removed and the customization and operation of channels have been simplified a lot. The old command syntax commands are now available as a contrib. 
- [Help System](../Components/Help-System.md) was refactored. 
	- A new type of `FileHelp` system allows you to add in-game help files as external Python files. This means there are three ways to add help entries in Evennia:  1) Auto-generated from Command's code. 2) Manually added to the database from the `sethelp` command in-game and 3) Created as external Python files that Evennia loads and makes available in-game.
	- We now use  `lunr` search indexing for better `help` matching and suggestions. Also improve
	  the main help command's default listing output.
	- Help command now uses `view` lock to determine if cmd/entry shows in index and `read` lock to determine if it can be read. It used to be `view` in the role of the latter. 
	- `sethelp` command now warns if shadowing other help-types when creating a new entry.
	- Make `help` index output clickable for webclient/clients with MXP (PR by davewiththenicehat)
-  Rework of the [Web](../Components/Website.md) setup, into a much more consistent structure and update to latest Django. The `mygame/web/static_overrides` and `-template_overrides` were removed. The folders are now just `mygame/web/static` and `/templates` and handle the automatic copying of data behind the scenes. `app.css` to `website.css` for consistency. The old `prosimii-css` files were removed.
- [AttributeProperty](../Components/Attributes.md#using-attributeproperty)/[TagProperty](../Components/Tags.md) along with `AliasProperty` and `PermissionProperty` to allow managing Attributes, Tags, Aliases and Permissios on typeclasses in the same way as Django fields. This dramatically reduces the need to assign Attributes/Tags in `at_create_object` hook. 
- The old `MULTISESSION_MODE` was divided into smaller settings, for better controlling what happens when a user connects, if a character should be auto-created, and how many characters they can control at the same time. See [Connection-Styles](../Concepts/Connection-Styles.md) for a detailed explanation. 
- Evennia now supports custom `evennia` launcher commands (e.g. `evennia mycmd foo bar`). Add new commands as callables accepting `*args`, as `settings.EXTRA_LAUNCHER_COMMANDS = {'mycmd': 'path.to.callable', ...}`.


## Contribs

The `contrib` folder structure was changed from 0.9.5. All contribs are now in sub-folders and organized into categories. All import paths must be updated. See [Contribs overview](../Contribs/Contribs-Overview.md).

- New [Traits contrib](../Contribs/Contrib-Traits.md), converted and expanded from Ainneve project. (whitenoise, Griatch)
- New [Crafting contrib](../Contribs/Contrib-Crafting.md), adding a full crafting subsystem (Griatch)
- New [XYZGrid contrib](../Contribs/Contrib-XYZGrid.md), adding x,y,z grid coordinates with in-game map and pathfinding. Controlled outside of the game via custom evennia launcher command (Griatch)
- New [Command cooldown contrib](../Contribs/Contrib-Cooldowns.md) contrib for making it easier to manage commands using
  dynamic cooldowns between uses (owllex)
- New [Godot Protocol contrib](../Contribs/Contrib-Godotwebsocket.md) for connecting to Evennia from a client written in the open-source game engine [Godot](https://godotengine.org/) (ChrisLR).
- New [name_generator contrib](../Contribs/Contrib-Name-Generator.md) for building random real-world based or fantasy-names based on phonetic rules (InspectorCaracal)
- New [Buffs contrib](../Contribs/Contrib-Buffs.md) for managing temporary and permanent RPG status buffs effects (tegiminis)
-  The existing [RPSystem contrib](../Contribs/Contrib-RPSystem.md) was refactored and saw a speed boost (InspectorCaracal, other contributors) 

## Translations 

- New Latin (la) translation (jamalainm)
- New German (de) translation (Zhuraj)
- Updated Italian translation (rpolve)
- Updated Swedish translation

## Utils

- New `utils.format_grid` for easily displaying long lists of items in a block. This is now used for the default help display.
- Add `utils.repeat` and `utils.unrepeat` as shortcuts to TickerHandler add/remove, similar
  to how `utils.delay` is a shortcut for TaskHandler add.
- Add `utils/verb_conjugation` for automatic verb conjugation (English only). This
  is useful for implementing actor-stance emoting for sending a string to different targets.
- `utils.evmenu.ask_yes_no` is a helper function that makes it easy to ask a yes/no question
  to the user and respond to their input. This complements the existing `get_input` helper.
- New `tasks` command for managing tasks started with `utils.delay` (PR by davewiththenicehat)
- Add `.deserialize()` method to `_Saver*` structures to help completely
  decouple structures from database without needing separate import.
- Add `run_in_main_thread` as a helper for those wanting to code server code
  from a web view.
- Update `evennia.utils.logger` to use Twisted's new logging API. No change in Evennia API
  except more standard aliases logger.error/info/exception/debug etc can now be used.
- Made `utils.iter_to_str` format prettier strings, using Oxford comma.
- Move `create_*` functions into db managers, leaving `utils.create` only being
  wrapper functions (consistent with `utils.search`). No change of api otherwise.

## Locks

- New `search:` lock type used to completely hide an object from being found by
  the `DefaultObject.search` (`caller.search`) method. (CloudKeeper)
- New default for `holds()` lockfunc - changed from default of `True` to default of `False` in order to disallow dropping nonsensical things (such as things you don't hold). 

## Hook changes

- Changed all `at_before/after_*` hooks to `at_pre/post_*` for consistency
  across Evennia (the old names still work but are deprecated)
- New `at_pre_object_leave(obj, destination)` method on `Objects`. 
- New `at_server_init()` hook called before all other startup hooks for all
  startup modes. Used for more generic overriding (volund)
- New `at_pre_object_receive(obj, source_location)` method on Objects. Called on
  destination, mimicking behavior of `at_pre_move` hook - returning False will abort move.
- `Object.normalize_name` and `.validate_name` added to (by default) enforce latinify
  on character name and avoid potential exploits using clever Unicode chars (trhr)
- Make `object.search` support 'stacks=0' keyword - if ``>0``, the method will return
  N identical matches instead of triggering a multi-match error.
- Add `tags.has()` method for checking if an object has a tag or tags (PR by ChrisLR)
- Add `Msg.db_receiver_external` field to allowe external, string-id message-receivers.
- Add `$pron()` and `$You()` inlinefuncs for pronoun parsing in actor-stance strings using `msg_contents`.

## Command changes

- Change default multi-match syntax from `1-obj`, `2-obj` to `obj-1`, `obj-2`, which seems to be what most expect.
- Split `return_appearance` hook with helper methods and have it use a template
  string in order to make it easier to override.
- Command executions now done on copies to make sure `yield` don't cause crossovers. Add
  `Command.retain_instance` flag for reusing the same command instance.
- Allow sending messages with `page/tell` without a `=` if target name contains no spaces.
- The `typeclass` command will now correctly search the correct database-table for the target
  obj (avoids mistakenly assigning an AccountDB-typeclass to a Character etc).
- Merged `script` and `scripts` commands into one, for both managing global- and
  on-object Scripts. Moved `CmdScripts` and `CmdObjects` to `commands/default/building.py`.
- The `channel` commands replace all old channel-related commands, such as `cset` etc
- Expand `examine` command's code to much more extensible and modular. Show
  attribute categories and value types (when not strings).
	- Add ability to examine `/script` and `/channel` entities  with `examine` command.
- Add support for `$dbref()` and `$search` when assigning an Attribute value
  with the `set` command. This allows assigning real objects from in-game.
- Have `type/force` default to `update`-mode rather than `reset`mode and add more verbose
  warning when using reset mode.

## Coding improvement highlights

- The db pickle-serializer now checks for methods `__serialize_dbobjs__` and `__deserialize_dbobjs__` to allow custom packing/unpacking of nested dbobjs, to allow storing in Attribute. See [Attributes](../Components/Attributes.md) documentation.
- Add `ObjectParent` mixin to default game folder template as an easy, ready-made
  way to override features on all ObjectDB-inheriting objects easily.
  source location, mimicking behavior of `at_pre_move` hook - returning False will abort move.
- New Unit test parent classes, for use both in Evenia core and in mygame. Restructured unit tests to always honor default settings.
  
 
## Other

- Homogenize manager search methods to always return querysets and not sometimes querysets and sometimes lists.
- Attribute/NAttribute got a homogenous representation, using intefaces, both
  `AttributeHandler` and `NAttributeHandler` has same api now.
- Added `content_types` indexing to DefaultObject's ContentsHandler. (volund)
- Made most of the networking classes such as Protocols and the SessionHandlers
  replaceable via `settings.py` for modding enthusiasts. (volund)
- The `initial_setup.py` file can now be substituted in `settings.py` to customize
  initial game database state. (volund)
- Make IP throttle use Django-based cache system for optional persistence (PR by strikaco)
- In modules given by `settings.PROTOTYPE_MODULES`, spawner will now first look for a global
  list `PROTOTYPE_LIST` of dicts before loading all dicts in the module as prototypes.
  concept of a dynamically created `ChannelCmdSet`.
- Prototypes now allow setting `prototype_parent` directly to a prototype-dict.
  This makes it easier when dynamically building in-module prototypes.
- Make `@lazy_property` decorator create read/delete-protected properties. This is because it's used for handlers, and e.g. self.locks=[] is a common beginner mistake.
- Change `settings.COMMAND_DEFAULT_ARG_REGEX` default from `None` to a regex meaning that
  a space or `/` must separate the cmdname and args. This better fits common expectations.
- Add `settings.MXP_ENABLED=True` and `settings.MXP_OUTGOING_ONLY=True` as sane defaults, to avoid known security issues with players entering MXP links.
- Made `MonitorHandler.add/remove` support `category` for monitoring Attributes with a category (before only key was used, ignoring category entirely). 
 

