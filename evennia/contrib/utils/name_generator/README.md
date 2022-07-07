# Random Name Generator

Contribution by InspectorCaracal (2022)

A module for generating random names, both real-world and fantasy. Real-world
names can be generated either as first (personal) names, family (last) names, or
full names (first, optional middles, and last). The name data is from [Behind the Name](https://www.behindthename.com/)
and used under the [CC BY-SA 4.0 license](https://creativecommons.org/licenses/by-sa/4.0/).

Fantasy names are generated from basic phonetic rules, using CVC syllable syntax.

Both real-world and fantasy name generation can be extended to include additional
information via your game's `settings.py`

## Usage

Import the module where you need it with the following:
```py
from evennia.contrib.utils.name_generator import namegen
```

By default, all of the functions will return a string with one generated name.
If you specify more than one, or pass `return_list=True` as a keyword argument,
the returned value will be a list of strings.

The module is especially useful for naming newly-created NPCs, like so:
```py
npc_name = namegen.full_name()
npc_obj = create_object(key=npc_name, typeclass="typeclasses.characters.NPC")
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

If you want to replace all of the built-in name lists with your own, set
`NAMEGEN_REPLACE_LISTS = True`

## Generating Fantasy Names

Generating completely made-up names is done with the `fantasy_name` function. The
contrib comes with three built-in styles of names which you can use, or you can
put a dictionary of custom name rules into `settings.py`

Generating a fantasy name takes the ruleset key as the "style" keyword, and can
return either a single name or multiple names. By default, it will return a
single name in the built-in "harsh" style.

```py
>>> namegen.fantasy_name()
'Vhon'
>>> namegen.fantasy_name(num=3, style="fluid")
['Aewalisash', 'Ayi', 'Iaa']
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

Then you could generate names following that ruleset with
`namegen.fantasy_name(style="example_style")`.

#### syllable
The "syllable" field defines the structure of each syllable. C is consonant, V is vowel,
and parentheses mean it's optional. So, the example "(C)VC" means that every syllable
will always have a vowel followed by a consonant, and will *sometimes* have another
consonant at the beginning.

*Note:* While it's not standard, the contrib lets you nest parentheses, with each layer
being less likely to show up. Additionally, any other characters put into the syllable
structure - e.g. an apostrophe - will be read and inserted as written. Check out the
"alien" style rules in the module for an example of both.

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

They can be left out of custom rulesets entirely.

#### vowels
Works exactly like consonants, but is instead used for the vowel selection. Single-
or multi-character strings are equally fine, and you can increase the frequency of
any given vowel by putting it into the list multiple times.

#### length
A tuple with the minimum and maximum number of syllables a name can have.

When setting this, keep in mind how long your syllables can get! 4 syllables might
not seem like very many, but if you have a (C)(V)VC structure with one- and
two-letter phonemes, you can get up to eight characters per syllable.