# Random Name Generator

Contribution by InspectorCaracal (2022)

A module for generating random names, both real-world and fantasy. Real-world
names can be generated either as first (personal) names, family (last) names, or
full names (first, optional middles, and last). The name data is from [Behind the Name](https://www.behindthename.com/)
and used under the [CC BY-SA 4.0 license](https://creativecommons.org/licenses/by-sa/4.0/).

Fantasy names are generated from basic phonetic rules, using CVC syllable syntax.

Both real-world and fantasy name generation can be extended to include additional
information via your game's `settings.py`

## Installation

This is a stand-alone utility. Just import this module (`from evennia.contrib.utils import name_generator`) and use its functions wherever you like.

## Usage

Import the module where you need it with the following:
```py
from evennia.contrib.utils.name_generator import namegen
```

By default, all of the functions will return a string with one generated name.
If you specify more than one, or pass `return_list=True` as a keyword argument, the returned value will be a list of strings.

The module is especially useful for naming newly-created NPCs, like so:
```py
npc_name = namegen.full_name()
npc_obj = create_object(key=npc_name, typeclass="typeclasses.characters.NPC")
```

## Available Settings

These settings can all be defined in your game's `server/conf/settings.py` file.

- `NAMEGEN_FIRST_NAMES` adds a new list of first (personal) names.
- `NAMEGEN_LAST_NAMES` adds a new list of last (family) names.
- `NAMEGEN_REPLACE_LISTS` - set to `True` if you want to use only the names defined in your settings.
- `NAMEGEN_FANTASY_RULES` lets you add new phonetic rules for generating entirely made-up names. See the section "Custom Fantasy Name style rules" for details on how this should look.

Examples:
```py
NAMEGEN_FIRST_NAMES = [
		("Evennia", 'mf'),
		("Green Tea", 'f'),
	]

NAMEGEN_LAST_NAMES = [ "Beeblebrox", "Son of Odin" ]

NAMEGEN_FANTASY_RULES = {
  "example_style": {
			"syllable": "(C)VC",
			"consonants": [ 'z','z','ph','sh','r','n' ],
			"start": ['m'],
			"end": ['x','n'],
			"vowels": [ "e","e","e","a","i","i","u","o", ],
			"length": (2,4),
	}
}
```


## Generating Real Names

The contrib offers three functions for generating random real-world names:
`first_name()`, `family_name()`, and `full_name()`. If you want more than one name
generated at once, you can use the `num` keyword argument to specify how many.

Example:
```
>>> namegen.first_name(num=5)
['Genesis', 'Tali', 'Budur', 'Dominykas', 'Kamau']
```

The `first_name` function also takes a `gender` keyword argument to filter names
by gender association. 'f' for feminine, 'm' for masculine, 'mf' for feminine
_and_ masculine, or the default `None` to match any gendering.

The `full_name` function also takes the `gender` keyword, as well as `parts` which
defines how many names make up the full name. The minimum is two: a first name and
a last name. You can also generate names with the family name first by setting
the keyword arg `surname_first` to `True`

Example:
```
>>> namegen.full_name()
'Keeva Bernat'
>>> namegen.full_name(parts=4)
'Suzu Shabnam Kafka Baier'
>>> namegen.full_name(parts=3, surname_first=True)
'Ó Muircheartach Torunn Dyson'
>>> namegen.full_name(gender='f')
'Wikolia Ó Deasmhumhnaigh'
```

### Adding your own names

You can add additional names with the settings `NAMEGEN_FIRST_NAMES` and
`NAMEGEN_LAST_NAMES`

`NAMEGEN_FIRST_NAMES` should be a list of tuples, where the first value is the name
and then second value is the gender flag - 'm' for masculine-only, 'f' for feminine-
only, and 'mf' for either one.

`NAMEGEN_LAST_NAMES` should be a list of strings, where each item is an available
surname.

Examples:
```py
NAMEGEN_FIRST_NAMES = [
		("Evennia", 'mf'),
		("Green Tea", 'f'),
	]

NAMEGEN_LAST_NAMES = [ "Beeblebrox", "Son of Odin" ]
```

Set `NAMEGEN_REPLACE_LISTS = True` if you want your custom lists above to entirely replace the built-in lists rather than extend them.

## Generating Fantasy Names

Generating completely made-up names is done with the `fantasy_name` function. The
contrib comes with three built-in styles of names which you can use, or you can
put a dictionary of custom name rules into `settings.py`

Generating a fantasy name takes the ruleset key as the "style" keyword, and can
return either a single name or multiple names. By default, it will return a
single name in the built-in "harsh" style. The contrib also comes with "fluid" and "alien" styles.

```py
>>> namegen.fantasy_name()
'Vhon'
>>> namegen.fantasy_name(num=3, style="harsh")
['Kha', 'Kizdhu', 'Godögäk']
>>> namegen.fantasy_name(num=3, style="fluid")
['Aewalisash', 'Ayi', 'Iaa']
>>> namegen.fantasy_name(num=5, style="alien")
["Qz'vko'", "Xv'w'hk'hxyxyz", "Wxqv'hv'k", "Wh'k", "Xbx'qk'vz"]
```

### Multi-Word Fantasy Names

The `fantasy_name` function will only generate one name-word at a time, so for multi-word names
you'll need to combine pieces together. Depending on what kind of end result you want, there are
several approaches.


#### The simple approach

If all you need is for it to have multiple parts, you can generate multiple names at once and `join` them.

```py
>>> name = " ".join(namegen.fantasy_name(num=2)
>>> print(name)
Dezhvözh Khäk
```

If you want a little more variation between first/last names, you can also generate names for
different styles and then combine them.

```py
>>> name = "{first} {last}".format( first=namegen.fantasy_name(style="fluid"), last=namegen.fantasy_name(style="harsh") )
>>> print(name)
Ofasa Käkudhu
```

#### "Nakku Silversmith"

One common fantasy name practice is profession- or title-based surnames. To achieve this effect,
you can use the `last_name` function with a custom list of last names and combine it with your generated
fantasy name.

Example:
```py
NAMEGEN_LAST_NAMES = [ "Silversmith", "the Traveller", "Destroyer of Worlds" ]
NAMEGEN_REPLACE_LISTS = True

>>> name = "{first} {last}".format( first=namegen.fantasy_name(), last=namegen.last_name() )
>>> print(name)
Tözhkheko the Traveller
```

#### Elarion d'Yrinea, Thror Obinson

Another common flavor of fantasy names is to use a surname suffix or prefix. For that, you'll
need to add in the extra bit yourself.

Examples:
```py
>>> names = namegen.fantasy_name(num=2)
>>> name = f"{names[0]} za'{names[1]}"
>>> print(name)
Tithe za'Dhudozkok

>>> names = namegen.fantasy_name(num=2)
>>> name = f"{names[0]} {names[1]}son"
>>> print(name)
Kön Ködhöddoson
```


### Custom Fantasy Name style rules

The style rules are contained in a dictionary of dictionaries, where the style name
is the key and the style rules are the dictionary value.

The following is how you would add a custom style to `settings.py`:
```py
NAMEGEN_FANTASY_RULES = {
  "example_style": {
			"syllable": "(C)VC",
			"consonants": [ 'z','z','ph','sh','r','n' ],
			"start": ['m'],
			"end": ['x','n'],
			"vowels": [ "e","e","e","a","i","i","u","o", ],
			"length": (2,4),
	}
}
```

Then you could generate names following that ruleset with `namegen.fantasy_name(style="example_style")`.

The keys `syllable`, `consonants`, `vowels`, and `length` must be present, and `length` must be the minimum and maximum syllable counts. `start` and `end` are optional.


#### syllable
The "syllable" field defines the structure of each syllable. C is consonant, V is vowel,
and parentheses mean it's optional. So, the example `(C)VC` means that every syllable
will always have a vowel followed by a consonant, and will *sometimes* have another
consonant at the beginning. e.g. `en`, `bak`

*Note:* While it's not standard, the contrib lets you nest parentheses, with each layer
being less likely to show up. Additionally, any other characters put into the syllable
structure - e.g. an apostrophe - will be read and inserted as written. The
"alien" style rules in the module gives an example of both: the syllable structure is `C(C(V))(')(C)`
which results in syllables such as `khq`, `xho'q`, and `q'` with a much lower frequency of vowels than
`C(C)(V)(')(C)` would have given.

#### consonants
A simple list of consonant phonemes that can be chosen from. Multi-character strings are
perfectly acceptable, such as "th", but each one will be treated as a single consonant.

The function uses a naive form of weighting, where you make a phoneme more likely to
occur by putting more copies of it into the list.

#### start and end
These are **optional** lists for the first and last letters of a syllable, if they're
a consonant. You can add on additional consonants which can only occur at the beginning
or end of a syllable, or you can add extra copies of already-defined consonants to
increase the frequency of them at the start/end of syllables.

For example, in the `example_style` above, we have a `start` of m, and `end` of x and n.
Taken with the rest of the consonants/vowels, this means you can have the syllables of `mez`
but not `zem`, and you can have `phex` or `phen` but not `xeph` or `neph`.

They can be left out of custom rulesets entirely.

#### vowels
Vowels is a simple list of vowel phonemes - exactly like consonants, but instead used for the
vowel selection. Single-or multi-character strings are equally fine. It uses the same naive weighting system
as consonants - you can increase the frequency of any given vowel by putting it into the list multiple times.

#### length
A tuple with the minimum and maximum number of syllables a name can have.

When setting this, keep in mind how long your syllables can get! 4 syllables might
not seem like very many, but if you have a (C)(V)VC structure with one- and
two-letter phonemes, you can get up to eight characters per syllable.