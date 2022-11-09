# Overview of the Evennia library

```{sidebar} API

    API stands for `Application Programming Interface`, a description for how to access
    the resources of a program or library.
```
A good place to start exploring Evennia is the [Evenia-API frontpage](../../../Evennia-API.md).
This page sums up the main components of Evennia with a short description of each. Try clicking through
to a few entries - once you get deep enough you'll see full descriptions
of each component along with their documentation. You can also click `[source]` to see the full Python source
for each thing.

You can also browse [the evennia repository on github](https://github.com/evennia/evennia). This is exactly
what you can download from us. The github repo is also searchable.

Finally, you can clone the evennia repo to your own computer and read the sources locally. This is necessary
if you want to help with Evennia's development itself. See the
  [extended install instructions](../../../Setup/Installation-Git.md) if you want to do this.

## Where is it?

If Evennia is installed, you can import from it simply with

    import evennia
    from evennia import some_module
    from evennia.some_module.other_module import SomeClass

and so on.

If you installed Evennia with `pip install`, the library folder will be installed deep inside your Python
installation. If you cloned the repo there will be a folder `evennia` on your hard drive there.

If you cloned the repo or read the code on `github` you'll find this being the outermost structure:

    evennia/
        bin/
        CHANGELOG.md
        ...
        ...
        docs/
        evennia/

This outer layer is for Evennia's installation and package distribution. That internal folder `evennia/evennia/` is
the _actual_ library, the thing covered by the API auto-docs and what you get when you do `import evennia`.

> The `evennia/docs/` folder contains the sources for this documentation. See
> [contributing to the docs](../../../Contributing-Docs.md) if you want to learn more about how this works.

This the the structure of the Evennia library:

 - evennia
   - [`__init__.py`](../../../Evennia-API.md#shortcuts) - The "flat API" of Evennia resides here.
   - [`settings_default.py`](../../../Setup/Settings.md#settings-file) - Root settings of Evennia. Copy settings
from here to `mygame/server/settings.py` file.
   - [`commands/`](../../../Components/Commands.md) - The command parser and handler.
     - `default/` - The [default commands](../../../Components/Default-Commands.md) and cmdsets.
   - [`comms/`](../../../Components/Channels.md) - Systems for communicating in-game.
   - `contrib/` - Optional plugins too game-specific for core Evennia.
   - `game_template/` - Copied to become the "game directory" when using `evennia --init`.
   - [`help/`](../../../Components/Help-System.md) - Handles the storage and  creation of help entries.
   - `locale/` - Language files ([i18n](../../../Concepts/Internationalization.md)).
   - [`locks/`](../../../Components/Locks.md) - Lock system for restricting access to in-game entities.
   - [`objects/`](../../../Components/Objects.md) - In-game entities (all types of items and Characters).
   - [`prototypes/`](../../../Components/Prototypes.md) - Object Prototype/spawning system and OLC menu
   - [`accounts/`](../../../Components/Accounts.md) - Out-of-game Session-controlled entities (accounts, bots etc)
   - [`scripts/`](../../../Components/Scripts.md) - Out-of-game entities equivalence to Objects, also with timer support.
   - [`server/`](../../../Components/Portal-And-Server.md) - Core server code and Session handling.
     - `portal/` - Portal proxy and connection protocols.
   - [`typeclasses/`](../../../Components/Typeclasses.md) - Abstract classes for the typeclass storage and database system.
   - [`utils/`](../../../Components/Coding-Utils.md) - Various miscellaneous useful coding resources.
   - [`web/`](../../../Concepts/Web-Features.md) - Web resources and webserver. Partly copied into game directory on initialization.

```{sidebar} __init__.py

    The `__init__.py` file is a special Python filename used to represent a Python 'package'.
    When you import `evennia` on its own, you import this file. When you do `evennia.foo` Python will
    first look for a property `.foo` in `__init__.py` and then for a module or folder of that name
    in the same location.

```

While all the actual Evennia code is found in the various folders, the `__init__.py` represents the entire
package `evennia`. It contains "shortcuts" to code that is actually located elsewhere. Most of these shortcuts
are listed if you [scroll down a bit](../../../Evennia-API.md) on the Evennia-API page.

## An example of exploring the library

In the previous lesson we took a brief look at `mygame/typeclasses/objects` as an example of a Python module. Let's
open it again. Inside is the `Object` class, which inherits from `DefaultObject`.
Near the top of the module is this line:

    from evennia import DefaultObject

We want to figure out just what this DefaultObject offers. Since this is imported directly from `evennia`, we
are actually importing from `evennia/__init__.py`.

[Look at Line 159](github:evennia/__init__.py#159) of `evennia/__init__.py` and you'll find this line:

    from .objects.objects import DefaultObject

```{sidebar} Relative and absolute imports

    The first full-stop in `from .objects.objects ...` means that
    we are importing from the current location. This is called a `relative import`.
    By comparison, `from evennia.objects.objects` is an `absolute import`. In this particular
    case, the two would give the same result.
```

> You can also look at [the right section of the API frontpage](../../../Evennia-API.md#typeclasses) and click through
> to the code that way.

The fact that `DefaultObject` is imported into `__init__.py` here is what makes it possible to also import
it as `from evennia import DefaultObject` even though the code for the class is not actually here.

So to find the code for `DefaultObject` we need to look in `evennia/objects/objects.py`. Here's how
to look it up in the docs:

1. Open the [API frontpage](../../../Evennia-API.md)
2. Locate the link to [evennia.objects.objects](../../../api/evennia.objects.objects.md) and click on it.
3 You are now in the python module. Scroll down (or search in your web browser) to find the `DefaultObject` class.
4 You can now read what this does and what methods are on it. If you want to see the full source, click the
   \[source\] link next to it.
