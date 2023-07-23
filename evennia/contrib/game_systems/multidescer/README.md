# Evennia Multidescer

Contribution by Griatch 2016

A "multidescer" is a concept from the MUSH world. It allows for
splitting your descriptions into arbitrary named 'sections' which you can
then swap out at will. It is a way for quickly managing your look (such as when
changing clothes) in more free-form roleplaying systems. This will also
work well together with the `rpsystem` contrib.

This multidescer will not require any changes to the Character class, rather it
will use the `multidescs` Attribute (a list) and create it if it does not exist.
It adds a new `+desc` command (where the + is optional in Evennia).

## Installation

Like for any custom command, you just add the new `+desc` command to a default
cmdset: Import the `evennia.contrib.game_systems.multidescer.CmdMultiDesc` into
`mygame/commands/default_cmdsets.py` and add it to the `CharacterCmdSet` class.

Reload the server and you should have the `+desc` command available (it
will replace the default `desc` command).

## Usage

Use the `+desc` command in-game:

    +desc [key]                - show current desc desc with <key>
    +desc <key> = <text>       - add/replace desc with <key>
    +desc/list                 - list descriptions (abbreviated)
    +desc/list/full            - list descriptions (full texts)
    +desc/edit <key>           - add/edit desc <key> in line editor
    +desc/del <key>            - delete desc <key>
    +desc/swap <key1>-<key2>   - swap positions of <key1> and <key2> in list
    +desc/set <key> [+key+...] - set desc as default or combine multiple descs

As an example, you can set one description for clothing, another for your boots,
hairstyle or whatever you like. Use `|/` to add line breaks for multi-line descriptions and
paragraphs, as well as `|_` to enforce indentations and whitespace (we don't
include colors in the example since they don't show in this documentation).

    +desc base = A handsome man.|_
    +desc mood = He is cheerful, like all is going his way.|/|/
    +desc head = On his head he has a red hat with a feather in it.|_
    +desc shirt = His chest is wrapped in a white shirt. It has golden buttons.|_
    +desc pants = He wears blue pants with a dragorn pattern on them.|_
    +desc boots = His boots are dusty from the road.
    +desc/set base + mood + head + shirt + pants + boots

When looking at this character, you will now see (assuming auto-linebreaks)

    A hansome man. He is cheerful, like all is going his way.

    On his head he has a red hat with a feather in it. His chest is wrapped in a
    white shirt. It has golden buttons. He wears blue pants with a dragon
    pattern on them. His boots are dusty from the road.

If you now do

    +desc mood = He looks sullen and forlorn.|/|/
    +desc shirt = His formerly white shirt is dirty and has a gash in it.|_

Your description will now be

    A handsome man. He looks sullen and forlorn.

    On his head he as a red hat with a feathre in it. His formerly white shirt
    is dirty and has a gash in it. He wears blue pants with a pattern on them.
    His boots are dusty from the road.

You can use any number of 'pieces' to build up your description, and can swap
and replace them as you like and RP requires.
