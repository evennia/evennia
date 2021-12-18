# Roleplaying base system for Evennia

Roleplaying emotes/sdescs - Griatch, 2015
Language/whisper emotes - Griatch, 2015

## Roleplaying emotes

This module contains the ContribRPObject, ContribRPRoom and
ContribRPCharacter typeclasses.  If you inherit your
objects/rooms/character from these (or make them the defaults) from
these you will get the following features:

- Objects/Rooms will get the ability to have poses and will report
  the poses of items inside them (the latter most useful for Rooms).
- Characters will get poses and also sdescs (short descriptions)
  that will be used instead of their keys. They will gain commands
  for managing recognition (custom sdesc-replacement), masking
  themselves as well as an advanced free-form emote command.

In more detail, This RP base system introduces the following features
to a game, common to many RP-centric games:

- emote system using director stance emoting (names/sdescs).
    This uses a customizable replacement noun (/me, @ etc) to
    represent you in the emote. You can use /sdesc, /nick, /key or
    /alias to reference objects in the room. You can use any
    number of sdesc sub-parts to differentiate a local sdesc, or
    use /1-sdesc etc to differentiate them. The emote also
    identifies nested says and separates case.
- sdesc obscuration of real character names for use in emotes
    and in any referencing such as object.search().  This relies
    on an SdescHandler `sdesc` being set on the Character and
    makes use of a custom Character.get_display_name hook. If
    sdesc is not set, the character's `key` is used instead. This
    is particularly used in the emoting system.
- recog system to assign your own nicknames to characters, can then
    be used for referencing. The user may recog a user and assign
    any personal nick to them. This will be shown in descriptions
    and used to reference them. This is making use of the nick
    functionality of Evennia.
- masks to hide your identity (using a simple lock).
- pose system to set room-persistent poses, visible in room
    descriptions and when looking at the person/object.  This is a
    simple Attribute that modifies how the characters is viewed when
    in a room as sdesc + pose.
- in-emote says, including seamless integration with language
    obscuration routine (such as contrib/rplanguage.py)

### Installation:

Add `RPSystemCmdSet` from this module to your CharacterCmdSet:

```python
# mygame/commands/default_cmdsets.py

# ...

from evennia.contrib.rpg.rpsystem import RPSystemCmdSet  <---

class CharacterCmdSet(default_cmds.CharacterCmdset):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(RPSystemCmdSet())  # <---

```

You also need to make your Characters/Objects/Rooms inherit from
the typeclasses in this module:

```python
# in mygame/typeclasses/characters.py

from evennia.contrib.rpg import ContribRPCharacter

class Character(ContribRPCharacter):
    # ...

```

```python
# in mygame/typeclasses/objects.py

from evennia.contrib.rpg import ContribRPObject

class Object(ContribRPObject):
    # ...

```

```python
# in mygame/typeclasses/rooms.py

from evennia.contrib.rpg import ContribRPRoom

class Room(ContribRPRoom):
    # ...

```

You will then need to reload the server and potentially force-reload
your objects, if you originally created them without this.

Example for your character:

    > type/reset/force me = typeclasses.characters.Character


Examples:

> look
Tavern
The tavern is full of nice people

*A tall man* is standing by the bar.

Above is an example of a player with an sdesc "a tall man". It is also
an example of a static *pose*: The "standing by the bar" has been set
by the player of the tall man, so that people looking at him can tell
at a glance what is going on.

> emote /me looks at /Tall and says "Hello!"

I see:
    Griatch looks at Tall man and says "Hello".
Tall man (assuming his name is Tom) sees:
    The godlike figure looks at Tom and says "Hello".

Note that by default, the case of the tag matters, so `/tall` will
lead to 'tall man' while `/Tall` will become 'Tall man' and /TALL
becomes /TALL MAN. If you don't want this behavior, you can pass
case_sensitive=False to the `send_emote` function.


##  Language and whisper obfuscation system

This module is intented to be used with an emoting system (such as
`contrib/rpg/rpsystem.py`). It offers the ability to obfuscate spoken words
in the game in various ways:

- Language: The language functionality defines a pseudo-language map
    to any number of languages.  The string will be obfuscated depending
    on a scaling that (most likely) will be input as a weighted average of
    the language skill of the speaker and listener.
- Whisper: The whisper functionality will gradually "fade out" a
    whisper along as scale 0-1, where the fading is based on gradually
    removing sections of the whisper that is (supposedly) easier to
    overhear (for example "s" sounds tend to be audible even when no other
    meaning can be determined).


### Installation

This module adds no new commands; embed it in your say/emote/whisper commands.

### Usage:

```python
from evennia.contrib import rplanguage

# need to be done once, here we create the "default" lang
rplanguage.add_language()

say = "This is me talking."
whisper = "This is me whispering.

print rplanguage.obfuscate_language(say, level=0.0)
<<< "This is me talking."
print rplanguage.obfuscate_language(say, level=0.5)
<<< "This is me byngyry."
print rplanguage.obfuscate_language(say, level=1.0)
<<< "Daly ly sy byngyry."

result = rplanguage.obfuscate_whisper(whisper, level=0.0)
<<< "This is me whispering"
result = rplanguage.obfuscate_whisper(whisper, level=0.2)
<<< "This is m- whisp-ring"
result = rplanguage.obfuscate_whisper(whisper, level=0.5)
<<< "---s -s -- ---s------"
result = rplanguage.obfuscate_whisper(whisper, level=0.7)
<<< "---- -- -- ----------"
result = rplanguage.obfuscate_whisper(whisper, level=1.0)
<<< "..."

```

To set up new languages, import and use the `add_language()`
helper method in this module. This allows you to customize the
"feel" of the semi-random language you are creating. Especially
the `word_length_variance` helps vary the length of translated
words compared to the original and can help change the "feel" for
the language you are creating. You can also add your own
dictionary and "fix" random words for a list of input words.

Below is an example of "elvish", using "rounder" vowels and sounds:

```python
# vowel/consonant grammar possibilities
grammar = ("v vv vvc vcc vvcc cvvc vccv vvccv vcvccv vcvcvcc vvccvvcc "
           "vcvvccvvc cvcvvcvvcc vcvcvvccvcvv")

# all not in this group is considered a consonant
vowels = "eaoiuy"

# you need a representative of all of the minimal grammars here, so if a
# grammar v exists, there must be atleast one phoneme available with only
# one vowel in it
phonemes = ("oi oh ee ae aa eh ah ao aw ay er ey ow ia ih iy "
            "oy ua uh uw y p b t d f v t dh s z sh zh ch jh k "
            "ng g m n l r w")

# how much the translation varies in length compared to the original. 0 is
# smallest, higher values give ever bigger randomness (including removing
# short words entirely)
word_length_variance = 1

# if a proper noun (word starting with capitalized letter) should be
# translated or not. If not (default) it means e.g. names will remain
# unchanged across languages.
noun_translate = False

# all proper nouns (words starting with a capital letter not at the beginning
# of a sentence) can have either a postfix or -prefix added at all times
noun_postfix = "'la"

# words in dict will always be translated this way. The 'auto_translations'
# is instead a list or filename to file with words to use to help build a
# bigger dictionary by creating random translations of each word in the
# list *once* and saving the result for subsequent use.
manual_translations = {"the":"y'e", "we":"uyi", "she":"semi", "he":"emi",
                      "you": "do", 'me':'mi','i':'me', 'be':"hy'e", 'and':'y'}

rplanguage.add_language(key="elvish", phonemes=phonemes, grammar=grammar,
                         word_length_variance=word_length_variance,
                         noun_translate=noun_translate,
                         noun_postfix=noun_postfix, vowels=vowels,
                         manual_translations=manual_translations,
                         auto_translations="my_word_file.txt")

```

This will produce a decicively more "rounded" and "soft" language than the
default one. The few `manual_translations` also make sure to make it at least
look superficially "reasonable".

The `auto_translations` keyword is useful, this accepts either a
list or a path to a text-file (with one word per line). This listing
of words is used to 'fix' translations for those words according to the
grammatical rules. These translations are stored persistently as long as the
language exists.

This allows to quickly build a large corpus of translated words
that never change. This produces a language that seem moderately
consistent, since words like 'the' will always be translated to the same thing.
The disadvantage (or advantage, depending on your game) is that players can
end up learn what words mean even if their characters don't know the
langauge.
