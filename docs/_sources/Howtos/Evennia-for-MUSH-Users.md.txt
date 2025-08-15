# Evennia for MUSH Users

*This page is adopted from an article originally posted for the MUSH community [here on
musoapbox.net](https://musoapbox.net/topic/1150/evennia-for-mushers).*

[MUSH](https://en.wikipedia.org/wiki/MUSH)es are text multiplayer games traditionally used for
heavily roleplay-focused game styles. They are often (but not always) utilizing game masters and
human oversight over code automation. MUSHes are traditionally built on the TinyMUSH-family of game
servers, like PennMUSH, TinyMUSH, TinyMUX and RhostMUSH. Also their siblings
[MUCK](https://en.wikipedia.org/wiki/TinyMUCK) and [MOO](https://en.wikipedia.org/wiki/MOO) are
often mentioned together with MUSH since they all inherit from the same
[TinyMUD](https://en.wikipedia.org/wiki/MUD_trees#TinyMUD_family_tree) base. A major feature is the
ability to modify and program the game world from inside the game by using a custom scripting
language. We will refer to this online scripting as *softcode* here.

Evennia works quite differently from a MUSH both in its overall design and under the hood. The same
things are achievable, just in a different way. Here are some fundamental differences to keep in
mind if you are coming from the MUSH world.

## Developers vs Players

In MUSH, users tend to code and expand all aspects of the game from inside it using softcode. A MUSH
can thus be said to be managed solely by *Players* with different levels of access. Evennia on the
other hand, differentiates between the role of the *Player* and the *Developer*.

- An Evennia *Developer* works in Python from *outside* the game, in what MUSH would consider
“hardcode”. Developers implement larger-scale code changes and can fundamentally change how the game
works. They then load their changes into the running Evennia server. Such changes will usually not
drop any connected players.
- An Evennia *Player* operates from *inside* the game. Some staff-level players are likely to double
as developers. Depending on access level, players can modify and expand the game's world by digging
new rooms, creating new objects, alias commands, customize their experience and so on. Trusted staff
may get access to Python via the `@py` command, but this would be a security risk for normal Players
to use. So the *Player* usually operates by making use of the tools prepared for them by the
*Developer* - tools that can be as rigid or flexible as the developer desires.

## Collaborating on a game - Python vs Softcode

For a *Player*, collaborating on a game need not be too different between MUSH and Evennia. The
building and description of the game world can still happen mostly in-game using build commands,
using text tags and [inline functions](../Components/FuncParser.md) to prettify and customize the
experience. Evennia offers external ways to build a world but those are optional. There is also
nothing *in principle* stopping a Developer from offering a softcode-like language to Players if
that is deemed necessary.

For *Developers* of the game, the difference is larger: Code is mainly written outside the game in
Python modules rather than in-game on the command line. Python is a very popular and well-supported
language with tons of documentation and help to be found. The Python standard library is also a
great help for not having to reinvent the wheel. But that said, while Python is considered one of
the easier languages to learn and use it is undoubtedly very different from MUSH softcode.

While softcode allows collaboration in-game, Evennia's external coding instead opens up the
possibility for collaboration using professional version control tools and bug tracking using
websites like github (or bitbucket for a free private repo). Source code can be written in proper
text editors and IDEs with refactoring, syntax highlighting and all other conveniences. In short,
collaborative development of an Evennia game is done in the same way most professional collaborative
development is done in the world, meaning all the best tools can be used.

## `@parent` vs `@typeclass` and `@spawn`

Inheritance works differently in Python than in softcode. Evennia has no concept of a "master
object" that other objects inherit from. There is in fact no reason at all to introduce "virtual
objects" in the game world - code and data are kept separate from one another.

In Python (which is an [object oriented](https://en.wikipedia.org/wiki/Object-oriented_programming)
language) one instead creates *classes* - these are like blueprints from which you spawn any number
of *object instances*. Evennia also adds the extra feature that every instance is persistent in the
database (this means no SQL is ever needed). To take one example, a unique  character in Evennia is
an instances of the class `Character`.

One parallel to MUSH's `@parent` command may be Evennia's `@typeclass` command, which changes which
class an already existing object is an instance of. This way you can literally turn a `Character`
into a `Flowerpot` on the spot.

if you are new to object oriented design it's important to note that all object instances of a class
does *not* have to be identical. If they did, all Characters would be named the same. Evennia allows
to customize individual objects in many different ways. One way is through *Attributes*, which are
database-bound properties that can be linked to any object. For example, you could have an `Orc`
class that defines all the stuff an Orc should be able to do (probably in turn inheriting from some
`Monster` class shared by all monsters). Setting different Attributes on different instances
(different strength, equipment, looks etc) would make each Orc unique despite all sharing the same
class.

 The `@spawn` command allows one to conveniently choose between different "sets" of Attributes to
put on each new Orc (like the "warrior" set or "shaman" set) . Such sets can even inherit one
another which is again somewhat remniscent at least of the *effect* of  `@parent` and the object-
based inheritance of MUSH.

There are other differences for sure, but that should give some feel for things. Enough with the
theory. Let's get down to more practical  matters next. To install, see the 
[Getting Started instructions](../Setup/Installation.md).

## A first step making things more familiar

We will here give two examples of customizing Evennia to be more familiar to a MUSH *Player*.

### Activating a multi-descer

By default Evennia’s `desc` command updates your description and that’s it. There is a more feature-
rich optional “multi-descer” in `evennia/contrib/multidesc.py` though. This alternative allows for
managing and combining a multitude of keyed descriptions.

To activate the multi-descer, `cd` to your game folder and into the `commands` sub-folder. There
you’ll find the file `default_cmdsets.py`. In Python lingo all `*.py` files are called *modules*.
Open the module in a text editor. We won’t go into Evennia in-game *Commands* and *Command sets*
further here, but suffice to say Evennia allows you to change which commands (or versions of
commands) are available to the player from moment to moment depending on circumstance.

Add two new lines to the module as seen below:

```python
# the file mygame/commands/default_cmdsets.py
# [...] 

from evennia.contrib import multidescer   # <- added now

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The CharacterCmdSet contains general in-game commands like look,
    get etc available on in-game Character objects. It is merged with
    the AccountCmdSet when an Account puppets a Character.
    """
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(multidescer.CmdMultiDesc())      # <- added now 
# [...]
```

Note that Python cares about indentation, so make sure to indent with the same number of spaces as
shown above!

So what happens above? We [import the
module](https://www.linuxtopia.org/online_books/programming_books/python_programming/python_ch28s03.html)
`evennia/contrib/multidescer.py` at the top. Once imported we can access stuff inside that module
using full stop (`.`). The multidescer is defined as a class `CmdMultiDesc` (we could find this out
by opening said module in a text editor). At the bottom we create a new instance of this class and
add it to the `CharacterCmdSet` class. For the sake of this tutorial we only need to know that
`CharacterCmdSet` contains all commands that should be be available to the `Character` by default.

This whole thing will be triggered when the command set is first created, which happens on server
start. So we need to reload Evennia with `@reload` - no one will be disconnected by doing this. If
all went well you should now be able to use `desc` (or `+desc`) and find that you have more
possibilities:

```text
> help +desc                  # get help on the command
> +desc eyes = His eyes are blue. 
> +desc basic = A big guy.
> +desc/set basic + + eyes    # we add an extra space between
> look me
A big guy. His eyes are blue.
```

If there are errors,  a *traceback* will show in the server log - several lines of text showing
where the error occurred. Find where the error is by locating the line number related to the
`default_cmdsets.py` file (it's the only one you've changed so far). Most likely you mis-spelled
something or missed the indentation. Fix it and either `@reload` again or run `evennia start` as
needed.

### Customizing the multidescer syntax 

As seen above the multidescer uses syntax like this  (where `|/` are Evennia's tags for line breaks)
:

```text
> +desc/set basic + |/|/ + cape + footwear + |/|/ + attitude 
``` 

This use of `+ ` was prescribed by the *Developer* that coded this `+desc` command. What if the
*Player* doesn’t like this syntax though? Do players need to pester the dev to change it? Not
necessarily. While Evennia does not allow the player to build their own multi-descer on the command
line, it does allow for *re-mapping* the command syntax to one they prefer. This is done using the
`nick` command.

Here’s a nick that changes how to input the command above: 

```text
> nick setdesc $1 $2 $3 $4 = +desc/set $1 + |/|/ + $2 + $3 + |/|/ + $4
```

The string on the left will be matched against your input and if matching, it will be replaced with
the string on the right. The `$`-type tags will store space-separated arguments and put them into
the replacement. The nick allows [shell-like wildcards](http://www.linfo.org/wildcard.html), so you
can use `*`, `?`, `[...]`, `[!...]` etc to match parts of the input.

The same description as before can now be set as 

```text
> setdesc basic cape footwear attitude 
```

With the `nick` functionality players can mitigate a lot of syntax dislikes even without the
developer changing the underlying Python code.

## Next steps

If you are a *Developer* and are interested in making a more MUSH-like Evennia game, a good start is
to look into the Evennia [Tutorial for a first MUSH-like game](./Tutorial-for-basic-MUSH-like-game.md).
That steps through building a simple little game from scratch and helps to acquaint you with the
various corners of Evennia. There is also the [Tutorial for running roleplaying sessions](Evennia-
for-roleplaying-sessions) that can be of interest.

An important aspect of making things more familiar for *Players* is adding new and tweaking existing
commands. How this is done is covered by the [Tutorial on adding new commands](Adding-Command-
Tutorial). You may also find it useful to shop through the `evennia/contrib/` folder. The 
[Tutorial world](Beginner-Tutorial/Part1/Beginner-Tutorial-Tutorial-World.md) is a small single-player quest you can try (it’s not very MUSH-
like but it does show many Evennia concepts in action). Beyond that there are [many more tutorials](./Howtos-Overview.md) 
to try out. If you feel you want a more visual overview you can also look at
[Evennia in pictures](https://evennia.blogspot.se/2016/05/evennia-in-pictures.html).

… And of course, if you need further help you can always drop into the [Evennia
chatroom](https://webchat.freenode.net/?channels=evennia&uio=MT1mYWxzZSY5PXRydWUmMTE9MTk1JjEyPXRydWUbb)
or post a question in our [forum/mailing list](https://groups.google.com/forum/#%21forum/evennia)!
