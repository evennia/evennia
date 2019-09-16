"""
Helper functions and classes for the evscaperoom contrib.

Most of these are available directly from wrappers in state/object/room classes
and does not need to be imported from here.

"""

import re
from random import choice
from evennia import create_object, search_object
from evennia.utils import justify, inherits_from

_BASE_TYPECLASS_PATH = "evscaperoom.objects."
_RE_PERSPECTIVE = re.compile(r"~(\w+)", re.I + re.U + re.M)
_RE_THING = re.compile(r"\*(\w+)", re.I + re.U + re.M)


def create_evscaperoom_object(
    typeclass=None, key="testobj", location=None, delete_duplicates=True, **kwargs
):
    """
    This is a convenience-wrapper for quickly building EvscapeRoom objects. This
    is called from the helper-method create_object on states, but is also useful
    for the object-create admin command.

    Note that for the purpose of the Evscaperoom, we only allow one instance
    of each *name*, deleting the old version if it already exists.

    Kwargs:
        typeclass (str): This can take just the class-name in the evscaperoom's
            objects.py module. Otherwise, a full path is needed.
        key (str): Name of object.
        location (Object): The location to create new object.
        delete_duplicates (bool): Delete old object with same key.
        kwargs (any): Will be passed into create_object.
    Returns:
        new_obj (Object): The newly created object, if any.


    """
    if not (
        callable(typeclass)
        or typeclass.startswith("evennia")
        or typeclass.startswith("typeclasses")
        or typeclass.startswith("evscaperoom")
    ):
        # unless we specify a full typeclass path or the class itself,
        # auto-complete it
        typeclass = _BASE_TYPECLASS_PATH + typeclass

    if delete_duplicates:
        old_objs = [
            obj
            for obj in search_object(key)
            if not inherits_from(obj, "evennia.objects.objects.DefaultCharacter")
        ]
        if location:
            # delete only matching objects in the given location
            [obj.delete() for obj in old_objs if obj.location == location]
        else:
            [obj.delete() for obj in old_objs]

    new_obj = create_object(typeclass=typeclass, key=key, location=location, **kwargs)
    return new_obj


def create_fantasy_word(length=5, capitalize=True):
    """
    Create a random semi-pronouncable 'word'.

    Kwargs:
        length (int): The desired length of the 'word'.
        capitalize (bool): If the return should be capitalized or not
    Returns:
        word (str): The fictous word of given length.

    """
    if not length:
        return ""

    phonemes = (
        "ea oh ae aa eh ah ao aw ai er ey ow ia ih iy oy ua "
        "uh uw a e i u y p b t d f v t dh "
        "s z sh zh ch jh k ng g m n l r w"
    ).split()
    word = [choice(phonemes)]
    while len(word) < length:
        word.append(choice(phonemes))
    # it's possible to exceed length limit due to double consonants
    word = "".join(word)[:length]
    return word.capitalize() if capitalize else word


# special word mappings when going from 2nd person to 3rd
irregulars = {
    "were": "was",
    "are": "is",
    "mix": "mixes",
    "push": "pushes",
    "have": "has",
    "focus": "focuses",
}


def parse_for_perspectives(string, you=None):
    """
    Parse a string with special markers to produce versions both
    intended for the person doing the action ('you') and for those
    seeing the person doing that action. Also marks 'things'
    according to style. See example below.

    Args:
        string (str): String on 2nd person form with ~ markers ('~you ~open ...')
        you (str): What others should see instead of you (Bob opens)
    Returns:
        second, third_person (tuple): Strings replace to be shown in 2nd and 3rd person
            perspective
    Example:
        "~You ~open"
        ->  "You open", "Bob opens"
    """

    def _replace_third_person(match):
        match = match.group(1)
        lmatch = match.lower()
        if lmatch == "you":
            return "|c{}|n".format(you)
        elif lmatch in irregulars:
            if match[0].isupper():
                return irregulars[lmatch].capitalize()
            return irregulars[lmatch]
        elif lmatch[-1] == "s":
            return match + "es"
        else:
            return match + "s"  # simple, most normal form

    you = "They" if you is None else you

    first_person = _RE_PERSPECTIVE.sub(r"\1", string)
    third_person = _RE_PERSPECTIVE.sub(_replace_third_person, string)
    return first_person, third_person


def parse_for_things(string, things_style=2, clr="|y"):
    """
    Parse string for special *thing markers and decorate
    it.

    Args:
        string (str): The string to parse.
        things_style (int): The style to handle `*things` marked:
            0 - no marking (remove `*`)
            1 - mark with color
            2 - mark with color and [] (default)
        clr (str): Which color to use for marker..
    Example:
        You open *door -> You open [door].
    """
    if not things_style:
        # hardcore mode - no marking of focus targets
        return _RE_THING.sub(r"\1", string)
    elif things_style == 1:
        # only colors
        return _RE_THING.sub(r"{}\1|n".format(clr), string)
    else:
        # colors and brackets
        return _RE_THING.sub(r"{}[\1]|n".format(clr), string)


def add_msg_borders(text):
    "Add borders above/below text block"
    maxwidth = max(len(line) for line in text.split("\n"))
    sep = "|w" + "~" * maxwidth + "|n"
    text = f"{sep}\n{text}\n{sep}"
    return text


def msg_cinematic(text, borders=True):
    """
    Display a text as a 'cinematic' - centered and
    surrounded by borders.

    Args:
        text (str): Text to format.
        borders (bool, optional): Put borders above and below text.
    Returns:
        text (str): Pretty-formatted text.

    """
    text = text.strip()
    text = justify(text, align="c", indent=1)
    if borders:
        text = add_msg_borders(text)
    return text
