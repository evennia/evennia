"""
Random Name Generator

Contribution by InspectorCaracal (2022)

A module for generating random names, both real-world and fantasy. Real-world
names can be generated either as first (personal) names, family (last) names, or
full names (first, optional middles, and last). The name data is from [Behind the Name](https://www.behindthename.com/)
and used under the [CC BY-SA 4.0 license](https://creativecommons.org/licenses/by-sa/4.0/).

Fantasy names are generated from basic phonetic rules, using CVC syllable syntax.

Both real-world and fantasy name generation can be extended to include additional
information via your game's `settings.py`


Available Methods:

  first_name   - Selects a random a first (personal) name from the name lists.
  last_name    - Selects a random last (family) name from the name lists.
  full_name    - Generates a randomized full name, optionally including middle names, by selecting first/last names from the name lists.
  fantasy_name - Generates a completely new made-up name based on phonetic rules.

Method examples:

>>> namegen.first_name(num=5)
['Genesis', 'Tali', 'Budur', 'Dominykas', 'Kamau']

>>> namegen.full_name(parts=3, surname_first=True)
'Ó Muircheartach Torunn Dyson'
>>> namegen.full_name(gender='f')
'Wikolia Ó Deasmhumhnaigh'

>>> namegen.fantasy_name(num=3, style="fluid")
['Aewalisash', 'Ayi', 'Iaa']


Available Settings (define these in your `settings.py`)

  NAMEGEN_FIRST_NAMES   - Option to add a new list of first (personal) names.
  NAMEGEN_LAST_NAMES    - Option to add a new list of last (family) names.
  NAMEGEN_REPLACE_LISTS - Set to True if you want to use ONLY your name lists and not the ones that come with the contrib.
  NAMEGEN_FANTASY_RULES - Option to add new fantasy-name style rules.
      Must be a dictionary that includes "syllable", "consonants", "vowels", and "length" - see the example.
      "start" and "end" keys are optional.

Settings examples:

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

"""

import random
import re
from os import path

from django.conf import settings

from evennia.utils.utils import is_iter

# Load name data from Behind the Name lists
dirpath = path.dirname(path.abspath(__file__))
_FIRSTNAME_LIST = []
with open(path.join(dirpath, "btn_givennames.txt"), "r", encoding="utf-8") as file:
    _FIRSTNAME_LIST = [
        line.strip().rsplit(" ") for line in file if line and not line.startswith("#")
    ]

_SURNAME_LIST = []
with open(path.join(dirpath, "btn_surnames.txt"), "r", encoding="utf-8") as file:
    _SURNAME_LIST = [line.strip() for line in file if line and not line.startswith("#")]

_REQUIRED_KEYS = {"syllable", "consonants", "vowels", "length"}
# Define phoneme structure for built-in fantasy name generators.
_FANTASY_NAME_STRUCTURES = {
    "harsh": {
        "syllable": "CV(C)",
        "consonants": [
            "k",
            "k",
            "k",
            "z",
            "zh",
            "g",
            "v",
            "t",
            "th",
            "w",
            "n",
            "d",
            "d",
        ],
        "start": [
            "dh",
            "kh",
            "kh",
            "kh",
            "vh",
        ],
        "end": [
            "n",
            "x",
        ],
        "vowels": [
            "o",
            "o",
            "o",
            "a",
            "y",
            "u",
            "u",
            "u",
            "ä",
            "ö",
            "e",
            "i",
            "i",
        ],
        "length": (1, 3),
    },
    "fluid": {
        "syllable": "V(C)",
        "consonants": [
            "r",
            "r",
            "l",
            "l",
            "l",
            "l",
            "s",
            "s",
            "s",
            "sh",
            "m",
            "n",
            "n",
            "f",
            "v",
            "w",
            "th",
        ],
        "start": [],
        "end": [],
        "vowels": [
            "a",
            "a",
            "a",
            "a",
            "a",
            "e",
            "i",
            "i",
            "i",
            "y",
            "u",
            "o",
        ],
        "length": (3, 5),
    },
    "alien": {
        "syllable": "C(C(V))(')(C)",
        "consonants": ["q", "q", "x", "z", "v", "w", "k", "h", "b"],
        "start": [
            "x",
        ],
        "end": [],
        "vowels": ["y", "w", "o", "y"],
        "length": (1, 5),
    },
}

_RE_DOUBLES = re.compile(r"(\w)\1{2,}")

# Load in optional settings

custom_first_names = (
    settings.NAMEGEN_FIRST_NAMES if hasattr(settings, "NAMEGEN_FIRST_NAMES") else []
)
custom_last_names = settings.NAMEGEN_LAST_NAMES if hasattr(settings, "NAMEGEN_LAST_NAMES") else []

if hasattr(settings, "NAMEGEN_FANTASY_RULES"):
    _FANTASY_NAME_STRUCTURES |= settings.NAMEGEN_FANTASY_RULES

if hasattr(settings, "NAMEGEN_REPLACE_LISTS") and settings.NAMEGEN_REPLACE_LISTS:
    _FIRSTNAME_LIST = custom_first_names or _FIRSTNAME_LIST
    _SURNAME_LIST = custom_last_names or _SURNAME_LIST

else:
    _FIRSTNAME_LIST += custom_first_names
    _SURNAME_LIST += custom_last_names


def fantasy_name(num=1, style="harsh", return_list=False):
    """
    Generate made-up names in one of a number of "styles".

    Keyword args:
        num (int)      - How many names to return.
        style (string) - The "style" of name. This references an existing algorithm.
        return_list (bool) - Whether to always return a list. `False` by default,
                which returns a string if there is only one value and a list if more.
    """

    def _validate(style_name):
        if style_name not in _FANTASY_NAME_STRUCTURES:
            raise ValueError(
                f"Invalid style name: '{style_name}'. Available style names: {' '.join(_FANTASY_NAME_STRUCTURES.keys())}"
            )
        style_dict = _FANTASY_NAME_STRUCTURES[style_name]

        if type(style_dict) is not dict:
            raise ValueError(f"Style {style_name} must be a dictionary.")

        keys = set(style_dict.keys())
        missing_keys = _REQUIRED_KEYS - keys
        if len(missing_keys):
            raise KeyError(
                f"Style dictionary {style_name} is missing required keys: {' '.join(missing_keys)}"
            )

        if not (type(style_dict["consonants"]) is list and type(style_dict["vowels"]) is list):
            raise TypeError(f"'consonants' and 'vowels' for style {style_name} must be lists.")

        if not (is_iter(style_dict["length"]) and len(style_dict["length"]) == 2):
            raise ValueError(
                f"'length' key for {style_name} must have a minimum and maximum number of syllables."
            )

        return style_dict

    # validate num first
    num = int(num)
    if num < 1:
        raise ValueError("Number of names to generate must be positive.")

    style_dict = _validate(style)

    syllable = []
    weight = 8
    # parse out the syllable structure with weights
    for key in style_dict["syllable"]:
        # parentheses mean optional - allow nested parens
        if key == "(":
            weight = weight / 2
        elif key == ")":
            weight = weight * 2
        else:
            if key == "C":
                sound_type = "consonants"
            elif key == "V":
                sound_type = "vowels"
            else:
                sound_type = key
            # append the sound type and weight
            syllable.append((sound_type, int(weight)))

    name_list = []

    # time to generate a name!
    for n in range(num):
        # build a list of syllables
        length = random.randint(*style_dict["length"])
        name = ""
        for i in range(length):
            # build the syllable itself
            syll = ""
            for sound, weight in syllable:
                # random chance to skip this key; lower weights mean less likely
                if random.randint(0, 8) > weight:
                    continue

                if sound not in style_dict:
                    # extra character, like apostrophes
                    syll += sound
                    continue

                # get a random sound from the sound list
                choices = list(style_dict[sound])

                if sound == "consonants":
                    # if it's a starting consonant, add starting-sounds to the options
                    if not len(syll):
                        choices += style_dict.get("start", [])
                    # if it's an ending consonant, add ending-sounds to the options
                    elif i + 1 == length:
                        choices += style_dict.get("end", [])

                syll += random.choice(choices)

            name += syll

        # condense repeating letters down to a maximum of 2
        name = _RE_DOUBLES.sub(lambda m: m.group(1) * 2, name)
        # capitalize the first letter
        name = name[0].upper() + name[1:] if len(name) > 1 else name.upper()
        name_list.append(name)

    if len(name_list) == 1 and not return_list:
        return name_list[0]
    return name_list


def first_name(
    num=1,
    gender=None,
    return_list=False,
):
    """
    Generate first names, also known as personal names.

    Keyword args:
        num (int)    - How many names to return.
        gender (str) - Restrict names by gender association. `None` by default, which selects from
                all possible names. Set to "m" for masculine, "f" for feminine, "mf" for androgynous
        return_list (bool) - Whether to always return a list. `False` by default,
                which returns a string if there is only one value and a list if more.
    """
    # validate num first
    num = int(num)
    if num < 1:
        raise ValueError("Number of names to generate must be positive.")

    if gender:
        # filter the options by gender
        name_options = [
            name_data[0]
            for name_data in _FIRSTNAME_LIST
            if all([gender_key in gender for gender_key in name_data[1]])
        ]
        if not len(name_options):
            raise ValueError(f"Invalid gender '{gender}'.")
    else:
        name_options = [name_data[0] for name_data in _FIRSTNAME_LIST]

    # take a random selection of `num` names, without repeats
    results = random.sample(name_options, num)

    if len(results) == 1 and not return_list:
        # return single value as a string
        return results[0]

    return results


def last_name(num=1, return_list=False):
    """
    Generate family names, also known as surnames or last names.

    Keyword args:
        num (int)    - How many names to return.
        return_list (bool) - Whether to always return a list. `False` by default,
                which returns a string if there is only one value and a list if more.
    """
    # validate num first
    num = int(num)
    if num < 1:
        raise ValueError("Number of names to generate must be positive.")

    # take a random selection of `num` names, without repeats
    results = random.sample(_SURNAME_LIST, num)

    if len(results) == 1 and not return_list:
        # return single value as a string
        return results[0]

    return results


def full_name(num=1, parts=2, gender=None, return_list=False, surname_first=False):
    """
    Generate complete names with a personal name, family name, and optionally middle names.

    Keyword args:
        num (int)    - How many names to return.
        parts (int)  - How many parts the name should have. By default two: first and last.
        gender (str) - Restrict names by gender association. `None` by default, which selects from
                all possible names. Set to "m" for masculine, "f" for feminine, "mf" for androgynous
        return_list (bool) - Whether to always return a list. `False` by default,
                which returns a string if there is only one value and a list if more.
        surname_first (bool) - Default `False`. Set to `True` if you want the family name to be
                placed at the beginning of the name instead of the end.
    """
    # validate num first
    num = int(num)
    if num < 1:
        raise ValueError("Number of names to generate must be positive.")
    # validate parts next
    parts = int(parts)
    if parts < 2:
        raise ValueError("Number of name parts to generate must be at least 2.")

    name_lists = []

    middle = parts - 2
    if middle:
        # calculate "middle" names.
        # we want them to be an intelligent mix of personal names and family names
        # first, split the total number of middle-name parts into "personal" and "family" at a random point
        total_mids = middle * num
        personals = random.randint(1, total_mids)
        familys = total_mids - personals
        # then get the names for each
        personal_mids = first_name(num=personals, gender=gender, return_list=True)
        family_mids = last_name(num=familys, return_list=True) if familys else []
        # splice them together according to surname_first....
        middle_names = family_mids + personal_mids if surname_first else personal_mids + family_mids
        # ...and then split into `num`-length lists to be used for the final names
        name_lists = [middle_names[num * i : num * (i + 1)] for i in range(0, middle)]

    # get personal and family names
    personal_names = first_name(num=num, gender=gender, return_list=True)
    last_names = last_name(num=num, return_list=True)

    # attach personal/family names to the list of name lists, according to surname_first
    if surname_first:
        name_lists = [last_names] + name_lists + [personal_names]
    else:
        name_lists = [personal_names] + name_lists + [last_names]

    # lastly, zip them all up and join them together
    names = list(zip(*name_lists))
    names = [" ".join(name) for name in names]

    if len(names) == 1 and not return_list:
        # return single value as a string
        return names[0]

    return names
