"""
English verb conjugation

Original Author: Tom De Smedt <tomdesmedt@organisms.be> of Nodebox
Refactored by Griatch 2021, for Evennia.

This is distributed under the GPL2 license. See ./LICENSE.txt for details.

The verb.txt morphology was adopted from the XTAG morph_englis.flat:
http://www.cis.upenn.edu/~xtag/


"""

import os

_VERBS_FILE = "verbs.txt"

# Each verb and its tenses is a list in verbs.txt,
# indexed according to the following keys:
# the negated forms (for supported verbs) are ind+11.

verb_tenses_keys = {
    "infinitive": 0,
    "1st singular present": 1,
    "2nd singular present": 2,
    "3rd singular present": 3,
    "present plural": 4,
    "present participle": 5,
    "1st singular past": 6,
    "2nd singular past": 7,
    "3rd singular past": 8,
    "past plural": 9,
    "past": 10,
    "past participle": 11,
}

# allow to specify tenses with a shorter notation
verb_tenses_aliases = {
    "inf": "infinitive",
    "1sgpres": "1st singular present",
    "2sgpres": "2nd singular present",
    "3sgpres": "3rd singular present",
    "pl": "present plural",
    "prog": "present participle",
    "1sgpast": "1st singular past",
    "2sgpast": "2nd singular past",
    "3sgpast": "3rd singular past",
    "pastpl": "past plural",
    "ppart": "past participle",
}

# Each verb has morphs for infinitve,
# 3rd singular present, present participle,
# past and past participle.
# Verbs like "be" have other morphs as well
# (i.e. I am, you are, she is, they aren't)
# Additionally, the following verbs can be negated:
# be, can, do, will, must, have, may, need, dare, ought.

# load the conjugation forms from ./verbs.txt
verb_tenses = {}

path = os.path.join(os.path.dirname(__file__), _VERBS_FILE)
with open(path) as fil:
    for line in fil.readlines():
        wordlist = [part.strip() for part in line.split(",")]
        verb_tenses[wordlist[0]] = wordlist

# Each verb can be lemmatised:
# inflected morphs of the verb point
# to its infinitive in this dictionary.
verb_lemmas = {}
for infinitive in verb_tenses:
    for tense in verb_tenses[infinitive]:
        if tense:
            verb_lemmas[tense] = infinitive


def verb_infinitive(verb):
    """
    Returns the uninflected form of the verb, like 'are' -> 'be'

    Args:
        verb (str): The verb to get the uninflected form of.

    Returns:
        str: The uninflected verb form of `verb`.

    """

    return verb_lemmas.get(verb, "")


def verb_conjugate(verb, tense="infinitive", negate=False):
    """
    Inflects the verb to the given tense.

    Args:
        verb (str): The single verb to conjugate.
        tense (str): The tense to convert to. This can be given either as a long or short form
            - "infinitive" ("inf") - be
            - "1st/2nd/3rd singular present" ("1/2/3sgpres") - am/are/is
            - "present plural" ("pl") - are
            - "present participle" ("prog") - being
            - "1st/2nd/3rd singular past" ("1/2/3sgpast") - was/were/was
            - "past plural" ("pastpl") - were
            - "past" - were
            - "past participle" ("ppart") - been
        negate (bool): Negates the verb. This only supported
            for a limited number of verbs: be, can, do, will, must, have, may,
            need, dare, ought.

    Returns:
        str: The conjugated verb. If conjugation fails, the original verb is returned.

    Examples:
        The verb 'be':
        - present: I am, you are, she is,
        - present participle: being,
        - past: I was, you were, he was,
        - past participle: been,
        - negated present: I am not, you aren't, it isn't.

    """
    tense = verb_tenses_aliases.get(tense, tense)
    verb = verb_infinitive(verb)
    ind = verb_tenses_keys[tense]
    if negate:
        ind += len(verb_tenses_keys)
    try:
        return verb_tenses[verb][ind]
    except IndexError:
        # TODO implement simple algorithm here with +s for certain tenses?
        return verb


def verb_present(verb, person="", negate=False):
    """
    Inflects the verb in the present tense.

    Args:
        person (str or int): This can be 1, 2, 3, "1st", "2nd", "3rd", "plural" or "*".
        negate (bool):  Some verbs like be, have, must, can be negated.

    Returns:
        str: The present tense verb.

    Example:
        had -> have

    """

    person = str(person).replace("pl", "*").strip("stndrgural")
    mapping = {
        "1": "1st singular present",
        "2": "2nd singular present",
        "3": "3rd singular present",
        "*": "present plural",
    }
    if person in mapping and verb_conjugate(verb, mapping[person], negate) != "":
        return verb_conjugate(verb, mapping[person], negate)

    return verb_conjugate(verb, "infinitive", negate)


def verb_present_participle(verb):
    """
    Inflects the verb in the present participle.

    Args:
        verb (str): The verb to inflect.

    Returns:
        str: The inflected verb.

    Examples:
        give -> giving, be -> being, swim -> swimming

    """
    return verb_conjugate(verb, "present participle")


def verb_past(verb, person="", negate=False):
    """

    Inflects the verb in the past tense.

    Args:
        verb (str): The verb to inflect.
        person (str, optional): The person can be specified with 1, 2, 3,
            "1st", "2nd", "3rd", "plural", "*".
        negate (bool, optional):  Some verbs like be, have, must, can be negated.

    Returns:
        str: The inflected verb.

    Examples:
        give -> gave, be -> was, swim -> swam

    """

    person = str(person).replace("pl", "*").strip("stndrgural")
    mapping = {
        "1": "1st singular past",
        "2": "2nd singular past",
        "3": "3rd singular past",
        "*": "past plural",
    }
    if person in mapping and verb_conjugate(verb, mapping[person], negate) != "":
        return verb_conjugate(verb, mapping[person], negate)

    return verb_conjugate(verb, "past", negate=negate)


def verb_past_participle(verb):
    """
    Inflects the verb in the present participle.

    Args:
        verb (str): The verb to inflect.

    Returns:
        str: The inflected verb.

    Examples:
        give -> given, be -> been, swim -> swum

    """
    return verb_conjugate(verb, "past participle")


def verb_all_tenses():
    """
    Get all all possible verb tenses.

    Returns:
        list: A list if string names.

    """

    return list(verb_tenses_keys.keys())


def verb_tense(verb):
    """
    Returns a string from verb_tenses_keys representing the verb's tense.

    Args:
        verb (str): The verb to check the tense of.

    Returns:
        str: The tense.

    Example:
        given -> "past participle"

    """
    infinitive = verb_infinitive(verb)
    data = verb_tenses[infinitive]
    for tense in verb_tenses_keys:
        if data[verb_tenses_keys[tense]] == verb:
            return tense
        if data[verb_tenses_keys[tense] + len(verb_tenses_keys)] == verb:
            return tense


def verb_is_tense(verb, tense):
    """
    Checks whether the verb is in the given tense.

    Args:
        verb (str): The verb to check.
        tense (str): The tense to check.

    Return:
        bool: If verb matches given tense.

    """
    tense = verb_tenses_aliases.get(tense, tense)
    return verb_tense(verb) == tense


def verb_is_present(verb, person="", negated=False):
    """
    Checks whether the verb is in the present tense.

    Args:
        verb (str): The verb to check.
        person (str): Check which person.
        negated (bool): Check if verb was negated.

    Returns:
        bool: If verb was in present tense.

    """

    person = str(person).replace("*", "plural")
    tense = verb_tense(verb)
    if tense is not None:
        if "present" in tense and person in tense:
            if not negated:
                return True
            elif "n't" in verb or " not" in verb:
                return True
    return False


def verb_is_present_participle(verb):
    """
    Checks whether the verb is in present participle.

    Args:
        verb (str): The verb to check.

    Returns:
        bool: Result of check.

    """

    tense = verb_tense(verb)
    return tense == "present participle"


def verb_is_past(verb, person="", negated=False):
    """
    Checks whether the verb is in the past tense.

    Args:
        verb (str): The verb to check.
        person (str): The person to check.
        negated (bool): Check if verb is negated.

    Returns:
        bool: Result of check.

    """

    person = str(person).replace("*", "plural")
    tense = verb_tense(verb)
    if tense is not None:
        if "past" in tense and person in tense:
            if not negated:
                return True
            elif "n't" in verb or " not" in verb:
                return True

    return False


def verb_is_past_participle(verb):
    """
    Checks whether the verb is in past participle.

    Args:
        verb (str): The verb to check.

    Returns:
        bool: The result of the check.

    """
    tense = verb_tense(verb)
    return tense == "past participle"


def verb_actor_stance_components(verb):
    """
    Figure out actor stance components of a verb.

    Args:
        verb (str): The verb to analyze

    Returns:
        tuple: The 2nd person (you) and 3rd person forms of the verb,
            in the same tense as the ingoing verb.

    """
    tense = verb_tense(verb)
    if "participle" in tense or "plural" in tense:
        return (verb, verb)
    if tense == "infinitive" or "present" in tense:
        you_str = verb_present(verb, person="2") or verb
        them_str = verb_present(verb, person="3") or verb + "s"
    else:
        you_str = verb_past(verb, person="2") or verb
        them_str = verb_past(verb, person="3") or verb + "s"
    return (you_str, them_str)
