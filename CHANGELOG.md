# Changelog

## Evennia 1.0 (2019-) (WIP)

- new `drop:holds()` lock default to limit dropping nonsensical things. Access check
  defaults to True for backwards-compatibility in 0.9, will be False in 1.0

### Already in master

- `py` command now reroutes stdout to output results in-game client. `py`
without arguments starts a full interactive Python console.
- Webclient default to a single input pane instead of two. Now defaults to no help-popup.
- Webclient fix of prompt display
- Webclient multimedia support for relaying images, video and sounds via
  `.msg(image=URL)`, `.msg(video=URL)`
  and `.msg(audio=URL)`
- Add Spanish translation (fermuch)
- Expand `GLOBAL_SCRIPTS` container to always start scripts and to include all
  global scripts regardless of how they were created.
- Change settings to always use lists instead of tuples, to make mutable
  settings easier to add to. (#1912)
- Make new `CHANNEL_MUDINFO` setting for specifying the mudinfo channel
- Make `CHANNEL_CONNECTINFO` take full channel definition
- Make `DEFAULT_CHANNELS` list auto-create channels missing at reload
- Webclient `ANSI->HTML` parser updated. Webclient line width changed from 1.6em to 1.1em
  to better make ANSI graphics look the same as for third-party clients
- `AttributeHandler.get(return_list=True)` will return `[]` if there are no
  Attributes instead of `[None]`.
- Remove `pillow` requirement (install especially if using imagefield)
- Add Simplified Korean translation (user aceamro)
- Show warning on `start -l` if settings contains values unsafe for production.
- Make code auto-formatted with Black.
- Make default `set` command able to edit nested structures (PR by Aaron McMillan)
- Allow running Evennia test suite from core repo with `make test`.
- Return `store_key` from `TickerHandler.add` and add `store_key` as a kwarg to 
  the `TickerHandler.remove` method. This makes it easier to manage tickers. 


## Evennia 0.9 (2018-2019)

### Distribution

- New requirement: Python 3.7 (py2.7 support removed)
- Django 2.1
- Twisted 19.2.1
- Autobahn websockets (removed old tmwx)
- Docker image updated

### Commands

- Remove `@`-prefix from all default commands (prefixes still work, optional)
- Removed default `@delaccount` command, incorporating as `@account/delete` instead. Added confirmation
  question.
- Add new `@force` command to have another object perform a command.
- Add the Portal uptime to the `@time` command.
- Make the `@link` command first make a local search before a global search.
- Have the default Unloggedin-look command look for optional `connection_screen()` callable in
  `mygame/server/conf/connection_screen.py`. This allows for more flexible welcome screens
  that are calculated on the fly.
- `@py` command now defaults to escaping html tags in its output when viewing in the webclient.
  Use new `/clientraw` switch to get old behavior (issue #1369).
- Shorter and more informative, dynamic, listing of on-command vars if not
  setting func() in child command class.
- New Command helper methods
  - `.client_width()` returns client width of the session running the command.
  - `.styled_table(*args, **kwargs)` returns a formatted evtable styled by user's options
  - `.style_header(*args, **kwargs)` creates styled header entry
  - `.style_separator(*args, **kwargs)`      "             separator
  - `.style_footer(*args, **kwargs)`         "             footer

### Web

- Change webclient from old txws version to use more supported/feature-rich Autobahn websocket library

#### Evennia game index

- Made Evennia game index client a part of core - now configured from settings file (old configs
  need to be moved)
- The `evennia connections` command starts a wizard that helps you connect your game to the game index.
- The game index now accepts games with no public telnet/webclient info (for early prototypes).

#### New golden-layout based Webclient UI (@friarzen)
- Features
  - Much slicker behavior and more professional look
  - Allows tabbing as well as click and drag of panes in any grid position
  - Renaming tabs, assignments of data tags and output types are simple per-pane menus now
  - Any number of input panes, with separate histories
  - Button UI (disabled in JS by default)

#### Web/Django standard initiative (@strikaco)
- Features
  - Adds a series of web-based forms and generic class-based views
    - Accounts
      - Register - Enhances registration; allows optional collection of email address
      - Form - Adds a generic Django form for creating Accounts from the web
    - Characters
      - Create - Authenticated users can create new characters from the website (requires associated form)
      - Detail - Authenticated and authorized users can view select details about characters
      - List - Authenticated and authorized users can browse a list of all characters
      - Manage - Authenticated users can edit or delete owned characters from the web
      - Form - Adds a generic Django form for creating characters from the web
    - Channels
      - Detail - Authorized users can view channel logs from the web
      - List - Authorized users can browse a list of all channels
    - Help Entries
      - Detail - Authorized users can view help entries from the web
      - List - Authorized users can browse a list of all help entries from the web
  - Navbar changes
    - Characters - Link to character list
    - Channels - Link to channel list
    - Help - Link to help entry list
    - Puppeting
      - Users can puppet their own characters within the context of the website
    - Dropdown
      - Link to create characters
      - Link to manage characters
      - Link to quick-select puppets
      - Link to password change workflow
- Functions
  - Updates Bootstrap to v4 stable
  - Enables use of Django Messages framework to communicate with users in browser
  - Implements webclient/website `_shared_login` functionality as Django middleware
  - 'account' and 'puppet' are added to all request contexts for authenticated users
  - Adds unit tests for all web views
- Cosmetic
  - Prettifies Django 'forgot password' workflow (requires SMTP to actually function)
  - Prettifies Django 'change password' workflow
- Bugfixes
  - Fixes bug on login page where error messages were not being displayed
  - Remove strvalue field from admin; it made no sense to have here, being an optimization field
    for internal use.

### Prototypes

- `evennia.prototypes.save_prototype` now takes the prototype as a normal
  argument (`prototype`) instead of having to give it as `**prototype`.
- `evennia.prototypes.search_prototype` has a new kwarg `require_single=False` that
  raises a KeyError exception if query gave 0 or >1 results.
- `evennia.prototypes.spawner` can now spawn by passing a `prototype_key`

### Typeclasses

- Add new methods on all typeclasses, useful specifically for object handling from the website/admin:
  + `web_get_admin_url()`: Returns the path to the object detail page in the Admin backend.
  + `web_get_create_url()`: Returns the path to the typeclass' creation page on the website, if implemented.
  + `web_get_absolute_url()`: Returns the path to the object's detail page on the website, if implemented.
  + `web_get_update_url()`: Returns the path to the object's update page on the website, if implemented.
  + `web_get_delete_url()`: Returns the path to the object's delete page on the website, if implemented.
- All typeclasses have new helper class method `create`, which encompasses useful functionality
  that used to be embedded for example in the respective `@create` or `@connect` commands.
- DefaultAccount now has new class methods implementing many things that used to be in unloggedin
  commands (these can now be customized on the class instead):
  + `is_banned()`: Checks if a given username or IP is banned.
  + `get_username_validators`: Return list of validators for username validation (see
    `settings.AUTH_USERNAME_VALIDATORS`)
  + `authenticate`: Method to check given username/password.
  + `normalize_username`: Normalizes names so (for Unicode environments) users cannot mimic existing usernames by replacing select characters with visually-similar Unicode chars.
  + `validate_username`: Mechanism for validating a username based on predefined Django validators.
  + `validate_password`: Mechanism for validating a password based on predefined Django validators.
  + `set_password`: Apply password to account, using validation checks.
- `AttributeHandler.remove` and `TagHandler.remove` can now be used to delete by-category. If neither
     key nor category is given, they now work the same as .clear().

### Protocols

- Support for `Grapevine` MUD-chat network ("channels" supported)

### Server

- Convert ServerConf model to store its values as a Picklefield (same as
    Attributes) instead of using a custom solution.
- OOB: Add support for MSDP LIST, REPORT, UNREPORT commands (re-mapped to `msdp_list`,
  `msdp_report`, `msdp_unreport`, inlinefuncs)
- Added `evennia.ANSIString` to flat API.
- Server/Portal log files now cycle to names on the form `server_.log_19_03_08_` instead of `server.log___19.3.8`, retaining
  unix file sorting order.
- Django signals fire for important events: Puppet/Unpuppet, Object create/rename, Login,
  Logout, Login fail Disconnect, Account create/rename

### Settings

- `GLOBAL_SCRIPTS` - dict defining typeclasses of global scripts to store on the new
  `evennia.GLOBAL_SCRIPTS` container. These will auto-start when Evennia start and will always
  exist.
- `OPTIONS_ACCOUNTS_DEFAULT` - option dict with option defaults and Option classes
- `OPTION_CLASS_MODULES` - classes representing an on-Account Option, on special form
- `VALIDATOR_FUNC_MODULES` - (general) text validator functions, for verifying an input
  is on a specific form.

### Utils

- `evennia` launcher now fully handles all django-admin commands, like running tests in parallel.
- `evennia.utils.create.account` now also takes `tags` and `attrs` keywords.
- `evennia.utils.interactive` decorator can now allow you to use yield(secs) to pause operation
  in any function, not just in Command.func. Likewise, response = yield(question) will work
  if the decorated function has an argument or kwarg `caller`.
- Added many more unit tests.
- Swap argument order of `evennia.set_trace` to `set_trace(term_size=(140, 40), debugger='auto')`
  since the size is more likely to be changed on the command line.
- `utils.to_str(text, session=None)` now acts as the old `utils.to_unicode` (which was removed).
  This converts to the str() type (not to a byte-string as in Evennia 0.8), trying different
  encodings. This function will also force-convert any object passed to it into a string (so
  `force_string` flag was removed and assumed always set).
- `utils.to_bytes(text, session=None)` replaces the old `utils.to_str()` functionality and converts
  str to bytes.
- `evennia.MONITOR_HANDLER.all` now takes keyword argument `obj` to only retrieve monitors from that specific
  Object (rather than all monitors in the entire handler).
- Support adding `\f` in command doc strings to force where EvMore puts page breaks.
- Validation Functions now added with standard API to homogenize user input validation.
- Option Classes added to make storing user-options easier and smoother.
- `evennia.VALIDATOR_CONTAINER` and `evennia.OPTION_CONTAINER` added to load these.

### Contribs

- Evscaperoom - a full puzzle engine for making multiplayer escape rooms in Evennia. Used to make
  the entry for the MUD-Coder's Guild's 2019 Game Jam with the theme "One Room", where it ranked #1.
- Evennia game-index client no longer a contrib - moved into server core and configured with new
  setting `GAME_INDEX_ENABLED`.
- The `extended_room` contrib saw some backwards-incompatible refactoring:
  + All commands now begin with `CmdExtendedRoom`. So before it was `CmdExtendedLook`, now
     it's `CmdExtendedRoomLook` etc.
  + The `detail` command was broken out of the `desc` command and is now a new, stand-alone command
     `CmdExtendedRoomDetail`.  This was done to make things easier to extend and to mimic how the detail
     command works in the tutorial-world.
  + The `detail` command now also supports deleting details (like the tutorial-world version).
  + The new `ExtendedRoomCmdSet` includes all the extended-room commands and is now the recommended way
     to install the extended-room contrib.
- Reworked `menu_login` contrib to use latest EvMenu standards. Now also supports guest logins.
- Mail contrib was refactored to have optional Command classes `CmdMail` for OOC+IC mail (added
    to the CharacterCmdSet and `CmdMailCharacter` for IC-only mailing between chars (added to CharacterCmdSet)

### Translations

- Simplified chinese, courtesy of user MaxAlex.


## Evennia 0.8 (2018)

### Requirements

- Up requirements to Django 1.11.x, Twisted 18 and pillow 5.2.0
- Add `inflect` dependency for automatic pluralization of object names.

### Server/Portal

- Removed `evennia_runner`, completely refactor `evennia_launcher.py` (the 'evennia' program)
  with different functionality).
- Both Portal/Server are now stand-alone processes (easy to run as daemon)
- Made Portal the AMP Server for starting/restarting the Server (the AMP client)
- Dynamic logging now happens using `evennia -l` rather than by interactive mode.
- Made AMP secure against erroneous HTTP requests on the wrong port (return error messages).
- The `evennia istart` option will start/switch the Server in foreground (interactive) mode, where it logs
  to terminal and can be stopped with Ctrl-C. Using `evennia reload`, or reloading in-game, will
  return Server to normal daemon operation.
- For validating passwords, use safe Django password-validation backend instead of custom Evennia one.
- Alias `evennia restart` to mean the same as `evennia reload`.

### Prototype changes

- New OLC started from `olc` command for loading/saving/manipulating prototypes in a menu.
- Moved evennia/utils/spawner.py into the new evennia/prototypes/ along with all new
  functionality around prototypes.
- A new form of prototype - database-stored prototypes, editable from in-game, was added. The old,
  module-created prototypes remain as read-only prototypes.
- All prototypes must have a key `prototype_key` identifying the prototype in listings. This is
  checked to be server-unique. Prototypes created in a module will use the global variable name they
  are assigned to if no `prototype_key` is given.
- Prototype field `prototype` was renamed to `prototype_parent` to avoid mixing terms.
- All prototypes must either have `typeclass` or `prototype_parent` defined. If using
  `prototype_parent`, `typeclass` must be defined somewhere in the inheritance chain. This is a
  change from Evennia 0.7 which allowed 'mixin' prototypes without `typeclass`/`prototype_key`. To
  make a mixin now, give it a default typeclass, like `evennia.objects.objects.DefaultObject`  and just
  override in the child as needed.
- Spawning an object using a prototype will automatically assign a new tag to it, named the same as
  the `prototype_key` and with the category `from_prototype`.
- The spawn command was extended to accept a full prototype on one line.
- The spawn command got the /save switch to save the defined prototype and its key
- The command spawn/menu will now start an OLC (OnLine Creation) menu to load/save/edit/spawn prototypes.

### EvMenu

- Added `EvMenu.helptext_formatter(helptext)`  to allow custom formatting of per-node help.
- Added `evennia.utils.evmenu.list_node` decorator for turning an EvMenu node into a multi-page listing.
- A `goto` option callable returning None (rather than the name of the next node) will now rerun the
  current node instead of failing.
- Better error handling of in-node syntax errors.
- Improve dedent of default text/helptext formatter. Right-strip whitespace.
- Add `debug` option when creating menu - this turns off persistence and makes the `menudebug`
  command available for examining the current menu state.


### Webclient

- Webclient now uses a plugin system to inject new components from the html file.
- Split-windows - divide input field into any number of horizontal/vertical panes and
  assign different types of server messages to them.
- Lots of cleanup and bug fixes.
- Hot buttons plugin (friarzen) (disabled by default).

### Locks

- New function `evennia.locks.lockhandler.check_lockstring`. This allows for checking an object
  against an arbitrary lockstring without needing the lock to be stored on an object first.
- New function `evennia.locks.lockhandler.validate_lockstring` allows for stand-alone validation
  of a lockstring.
- New function `evennia.locks.lockhandler.get_all_lockfuncs` gives a dict {"name": lockfunc} for
  all available lock funcs. This is useful for dynamic listings.


### Utils

- Added new `columnize` function for easily splitting text into multiple columns. At this point it
  is not working too well with ansi-colored text however.
- Extend the `dedent` function with a new `baseline_index` kwarg. This allows to force all lines to
  the indentation given by the given line regardless of if other lines were already a 0 indentation.
  This removes a problem with the original `textwrap.dedent` which will only dedent to the least
  indented part of a text.
- Added `exit_cmd` to EvMore pager, to allow for calling a command (e.g. 'look') when leaving the pager.
- `get_all_typeclasses` will return  dict `{"path": typeclass, ...}` for all typeclasses available
  in the system. This is used by the new `@typeclass/list` subcommand (useful for builders etc).
- `evennia.utils.dbserialize.deserialize(obj)` is a new helper function to *completely* disconnect
  a mutable recovered from an Attribute from the database. This will convert all nested `_Saver*`
  classes to their plain-Python counterparts.

### General

- Start structuring the `CHANGELOG` to list features in more detail.
- Docker image `evennia/evennia:develop` is now auto-built, tracking the develop branch.
- Inflection and grouping of multiple objects in default room (an box, three boxes)
- `evennia.set_trace()` is now a shortcut for launching pdb/pudb on a line in the Evennia event loop.
- Removed the enforcing of `MAX_NR_CHARACTERS=1` for `MULTISESSION_MODE` `0` and `1` by default.
- Add `evennia.utils.logger.log_sec` for logging security-related messages (marked SS in log).

### Contribs

- `Auditing` (Johnny): Log and filter server input/output for security purposes
- `Build Menu` (vincent-lg): New @edit command to edit object properties in a menu.
- `Field Fill` (Tim Ashley Jenkins): Wraps EvMenu for creating submittable forms.
- `Health Bar` (Tim Ashley Jenkins): Easily create colorful bars/meters.
- `Tree select` (Fluttersprite): Wrap EvMenu to create a common type of menu from a string.
- `Turnbattle suite` (Tim Ashley Jenkins)- the old `turnbattle.py` was moved into its own
  `turnbattle/` package and reworked with many different flavors of combat systems:
 - `tb_basic` - The basic turnbattle system, with initiative/turn order attack/defense/damage.
 - `tb_equip` - Adds weapon and armor, wielding, accuracy modifiers.
 - `tb_items` - Extends `tb_equip` with item use with conditions/status effects.
 - `tb_magic` - Extends `tb_equip` with spellcasting.
 - `tb_range` - Adds system for abstract positioning and movement.
 - The `extended_room` contrib saw some backwards-incompatible refactoring:
   - All commands now begin with `CmdExtendedRoom`. So before it was `CmdExtendedLook`, now
     it's `CmdExtendedRoomLook` etc.
   - The `detail` command was broken out of the `desc` command and is now a new, stand-alone command
     `CmdExtendedRoomDetail`.  This was done to make things easier to extend and to mimic how the detail
     command works in the tutorial-world.
   - The `detail` command now also supports deleting details (like the tutorial-world version).
   - The new `ExtendedRoomCmdSet` includes all the extended-room commands and is now the recommended way
     to install the extended-room contrib.
- Updates and some cleanup of existing contribs.


### Internationalization

- Polish translation by user ogotai

# Overviews

## Sept 2017:
Release of Evennia 0.7; upgrade to Django 1.11, change 'Player' to
'Account', rework the website template and a slew of other updates.
Info on what changed and how to migrate is found here:
https://groups.google.com/forum/#!msg/evennia/0JYYNGY-NfE/cDFaIwmPBAAJ

## Feb 2017:
New devel branch created, to lead up to Evennia 0.7.

## Dec 2016:
Lots of bugfixes and considerable uptick in contributors. Unittest coverage
and PEP8 adoption and refactoring.

## May 2016:
Evennia 0.6 with completely reworked Out-of-band system, making
the message path completely flexible and built around input/outputfuncs.
A completely new webclient, split into the evennia.js library and a
gui library, making it easier to customize.

## Feb 2016:
Added the new EvMenu and EvMore utilities, updated EvEdit and cleaned up
a lot of the batchcommand functionality. Started work on new Devel branch.

## Sept 2015:
Evennia 0.5. Merged devel branch, full library format implemented.

## Feb 2015:
Development currently in devel/ branch. Moved typeclasses to use
django's proxy functionality. Changed the Evennia folder layout to a
library format with a stand-alone launcher, in preparation for making
an 'evennia' pypy package and using versioning. The version we will
merge with will likely be 0.5. There is also work with an expanded
testing structure and the use of threading for saves. We also now
use Travis for automatic build checking.

## Sept 2014:
Updated to Django 1.7+ which means South dependency was dropped and
minimum Python version upped to 2.7. MULTISESSION_MODE=3 was added
and the web customization system was overhauled using the latest
functionality of django. Otherwise, mostly bug-fixes and
implementation of various smaller feature requests as we got used
to github. Many new users have appeared.

## Jan 2014:
Moved Evennia project from Google Code to github.com/evennia/evennia.

## Nov 2013:
Moved the internal webserver into the Server and added support for
out-of-band protocols (MSDP initially). This large development push
also meant fixes and cleanups of the way attributes were handled.
Tags were added, along with proper handlers for permissions, nicks
and aliases.

## May 2013:
Made players able to control more than one Character at the same
time, through the MULTISESSION_MODE=2 addition. This lead to a lot
of internal changes for the server.

## Oct 2012:
Changed Evennia from the Modified Artistic 1.0 license to the more
standard and permissive BSD license. Lots of updates and bug fixes as
more people start to use it in new ways. Lots of new caching and
speed-ups.

## March 2012:
Evennia's API has changed and simplified slightly in that the
base-modules where removed from game/gamesrc. Instead admins are
encouraged to explicitly create new modules under game/gamesrc/ when
they want to implement their game - gamesrc/ is empty by default
except for the example folders that contain template files to use for
this purpose. We also added the ev.py file, implementing a new, flat
API.  Work is ongoing to add support for mud-specific telnet
extensions, notably the MSDP and GMCP out-of-band extensions.  On the
community side, evennia's dev blog was started and linked on planet
Mud-dev aggregator.

## Nov 2011:
After creating several different proof-of-concept game systems (in
contrib and privately) as well testing lots of things to make sure the
implementation is basically sound, we are declaring Evennia out of
Alpha. This can mean as much or as little as you want, admittedly -
development is still heavy but the issue list is at an all-time low
and the server is slowly stabilizing as people try different things
with it. So Beta it is!

## Aug 2011:
Split Evennia into two processes: Portal and Server. After a lot of
work trying to get in-memory code-reloading to work, it's clear this
is not Python's forte - it's impossible to catch all exceptions,
especially in asynchronous code like this.  Trying to do so results in
hackish, flakey and unstable code. With the Portal-Server split, the
Server can simply be rebooted while players connected to the Portal
remain connected. The two communicates over twisted's AMP protocol.

## May 2011:
The new version of Evennia, originally hitting trunk in Aug2010, is
maturing. All commands from the pre-Aug version, including IRC/IMC2
support works again. An ajax web-client was added earlier in the year,
including moving Evennia to be its own webserver (no more need for
Apache or django-testserver). Contrib-folder added.

## Aug 2010:
Evennia-griatch-branch is ready for merging with trunk. This marks a
rather big change in the inner workings of the server, such as the
introduction of TypeClasses and Scripts (as compared to the old
ScriptParents and Events) but should hopefully bring everything
together into one consistent package as code development continues.

## May 2010:
Evennia is currently being heavily revised and cleaned from
the years of gradual piecemeal development. It is thus in a very
'Alpha' stage at the moment. This means that old code snippets
will not be backwards compatabile. Changes touch almost all
parts of Evennia's innards, from the way Objects are handled
to Events, Commands and Permissions.

## April 2010:
Griatch takes over Maintainership of the Evennia project from
the original creator Greg Taylor.

(Earlier revisions, with previous maintainer, go back to 2005)


# Contact, Support and Development

Make a post to the mailing list or chat us up on IRC. We also have a
bug tracker if you want to report bugs. Finally, if you are willing to
help with the code work, we much appreciate all help!  Visit either of
the following resources:

* Evennia Webpage
  http://evennia.com
* Evennia manual (wiki)
  https://github.com/evennia/evennia/wiki
* Evennia Code Page (See INSTALL text for installation)
  https://github.com/evennia/evennia
* Bug tracker
  https://github.com/evennia/evennia/issues
* IRC channel
  visit channel #evennia on irc.freenode.com
  or the webclient: http://tinyurl.com/evchat
