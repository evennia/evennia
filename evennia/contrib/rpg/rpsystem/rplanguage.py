"""
Language and whisper obfuscation system

Evennia contrib - Griatch 2015

This module is intented to be used with an emoting system (such as
contrib/rpsystem.py). It offers the ability to obfuscate spoken words
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

## Usage

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

## Custom languages

To set up new languages, you need to run `add_language()`
helper function in this module. The arguments of this function (see below)
are used to store the new language in the database (in the LanguageHandler,
which is a type of Script).

If you want to remember the language definitions, you could put them all
in a module along with the `add_language` call as a quick way to
rebuild the language on a db reset:

```python
# a stand-alone module somewhere under mygame. Just import this
# once to automatically add the language!

from evennia.contrib.rpg.rpsystem import rplanguage
grammar = (...)
vowels = "eaouy"
# etc

rplanguage.add_language(grammar=grammar, vowels=vowels, ...)
```

The variables of `add_language` allows you to customize the "feel" of
the semi-random language you are creating. Especially
the `word_length_variance` helps vary the length of translated
words compared to the original. You can also add your own
dictionary and "fix" random words for a list of input words.

## Example

Below is an example module creating "elvish", using "rounder" vowels and sounds:

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

This will produce a decicively more "rounded" and "soft" language
than the default one. The few manual_translations also make sure
to make it at least look superficially "reasonable".

The `auto_translations` keyword is useful, this accepts either a
list or a path to a file of words (one per line) to automatically
create fixed translations for according to the grammatical rules.
This allows to quickly build a large corpus of translated words
that never change (if this is desired).

"""
import re
from collections import defaultdict
from random import choice, randint

from evennia import DefaultScript
from evennia.utils import logger

# ------------------------------------------------------------
#
# Obfuscate language
#
# ------------------------------------------------------------

# default language grammar
_PHONEMES = (
    "ea oh ae aa eh ah ao aw ai er ey ow ia ih iy oy ua uh uw a e i u y p b t d f v t dh "
    "s z sh zh ch jh k ng g m n l r w"
)
_VOWELS = "eaoiuy"
# these must be able to be constructed from phonemes (so for example,
# if you have v here, there must exist at least one single-character
# vowel phoneme defined above)
_GRAMMAR = "v cv vc cvv vcc vcv cvcc vccv cvccv cvcvcc cvccvcv vccvccvc cvcvccvv cvcvcvcvv"

_RE_FLAGS = re.MULTILINE + re.IGNORECASE + re.DOTALL + re.UNICODE
_RE_GRAMMAR = re.compile(r"vv|cc|v|c", _RE_FLAGS)
_RE_WORD = re.compile(r"\w+", _RE_FLAGS)
# superfluous chars, except ` ... `
_RE_EXTRA_CHARS = re.compile(r"\s+(?!... )(?=\W)|[,.?;](?!.. )(?=[,?;]|\s+[,.?;])", _RE_FLAGS)


class LanguageError(RuntimeError):
    pass


class LanguageExistsError(LanguageError):
    pass


class LanguageHandler(DefaultScript):
    """
    This is a storage class that should usually not be created on its
    own. It's automatically created by a call to `obfuscate_language`
    or `add_language` below.

    Languages are implemented as a "logical" pseudo- consistent language
    algorith here. The idea is that a language is built up from
    phonemes. These are joined together according to a "grammar" of
    possible phoneme- combinations and allowed characters. It may
    sound simplistic, but this allows to easily make
    "similar-sounding" languages. One can also custom-define a
    dictionary of some common words to give further consistency.
    Optionally, the system also allows an input list of common words
    to be loaded and given random translations. These will be stored
    to disk and will thus not change. This gives a decent "stability"
    of the language but if the goal is to obfuscate, this may allow
    players to eventually learn to understand the gist of a sentence
    even if their characters can not. Any number of languages can be
    created this way.

    This nonsense language will partially replace the actual spoken
    language when so desired (usually because the speaker/listener
    don't know the language well enough).

    """

    def at_script_creation(self):
        "Called when script is first started"
        self.key = "language_handler"
        self.persistent = True
        self.db.language_storage = {}

    def add(
        self,
        key="default",
        phonemes=_PHONEMES,
        grammar=_GRAMMAR,
        word_length_variance=0,
        noun_translate=False,
        noun_prefix="",
        noun_postfix="",
        vowels=_VOWELS,
        manual_translations=None,
        auto_translations=None,
        force=False,
    ):
        """
        Add a new language. Note that you generally only need to do
        this once per language and that adding an existing language
        will re-initialize all the random components to new permanent
        values.

        Args:
            key (str, optional): The name of the language. This
                will be used as an identifier for the language so it
                should be short and unique.
            phonemes (str, optional): Space-separated string of all allowed
                phonemes in this language. If either of the base phonemes
                (c, v, cc, vv) are present in the grammar, the phoneme list must
                at least include one example of each.
            grammar (str): All allowed consonant (c) and vowel (v) combinations
                allowed to build up words. Grammars are broken into the base phonemes
                (c, v, cc, vv) prioritizing the longer bases. So cvv would be a
                the c + vv (would allow for a word like 'die' whereas
                cvcvccc would be c+v+c+v+cc+c (a word like 'galosch').
            word_length_variance (real): The variation of length of words.
                0 means a minimal variance, higher variance may mean words
                have wildly varying length; this strongly affects how the
                language "looks".
            noun_translate (bool, optional): If a proper noun should be translated or
                not. By default they will not, allowing for e.g. the names of characters
                to be understandable. A 'noun' is identified as a capitalized word
                *not at the start of a sentence*. This simple metric means that names
                starting a sentence always will be translated (- but hey, maybe
                the fantasy language just never uses a noun at the beginning of
                sentences, who knows?)
            noun_prefix (str, optional): A prefix to go before every noun
                in this language (if any).
            noun_postfix (str, optuonal): A postfix to go after every noun
                in this language (if any, usually best to avoid combining
                with `noun_prefix` or language becomes very wordy).
            vowels (str, optional): Every vowel allowed in this language.
            manual_translations (dict, optional): This allows for custom-setting
                certain words in the language to mean the same thing. It is
                on the form `{real_word: fictional_word}`, for example
                `{"the", "y'e"}` .
            auto_translations (str or list, optional): These are lists
                words that should be auto-translated with a random, but
                fixed, translation. If a path to a file, this file should
                contain a list of words to produce translations for, one
                word per line.  If a list, the list's elements should be
                the words to translate.  The `manual_translations` will
                always override overlapping translations created
                automatically.
            force (bool, optional): Unless true, will not allow the addition
                of a language that is already created.

        Raises:
            LanguageExistsError: Raised if trying to adding a language
                with a key that already exists, without `force` being set.
        Notes:
            The `word_file` is for example a word-frequency list for
            the N most common words in the host language. The
            translations will be random, but will be stored
            persistently to always be the same. This allows for
            building a quick, decently-sounding fictive language that
            tend to produce the same "translation" (mostly) with the
            same input sentence.

        """
        if key in self.db.language_storage and not force:
            raise LanguageExistsError(
                "Language is already created. Re-adding it will re-build"
                " its dictionary map. Use 'force=True' keyword if you are sure."
            )

        # create grammar_component->phoneme mapping
        # {"vv": ["ea", "oh", ...], ...}
        grammar2phonemes = defaultdict(list)
        for phoneme in phonemes.split():
            if re.search(r"\W", phoneme, re.U):
                raise LanguageError("The phoneme '%s' contains an invalid character." % phoneme)
            gram = "".join(["v" if char in vowels else "c" for char in phoneme])
            grammar2phonemes[gram].append(phoneme)

        # allowed grammar are grouped by length
        gramdict = defaultdict(list)
        for gram in grammar.split():
            if re.search(r"\W|(!=[cv])", gram):
                raise LanguageError(
                    "The grammar '%s' is invalid (only 'c' and 'v' are allowed)" % gram
                )
            gramdict[len(gram)].append(gram)
        grammar = dict(gramdict)

        # create automatic translation
        translation = {}

        if auto_translations:
            if isinstance(auto_translations, str):
                # path to a file rather than a list
                with open(auto_translations, "r") as f:
                    auto_translations = f.readlines()
            for word in auto_translations:
                word = word.strip()
                lword = len(word)
                new_word = ""
                wlen = max(0, lword + sum(randint(-1, 1) for i in range(word_length_variance)))
                if wlen not in grammar:
                    # always create a translation, use random length
                    structure = choice(grammar[choice(list(grammar))])
                else:
                    # use the corresponding length
                    structure = choice(grammar[wlen])
                for match in _RE_GRAMMAR.finditer(structure):
                    try:
                        new_word += choice(grammar2phonemes[match.group()])
                    except IndexError:
                        raise IndexError(
                            "Could not find a matching phoneme for the grammar "
                            f"'{match.group()}'. Make there is at least one phoneme matching this "
                            "combination of consonants and vowels."
                        )
                translation[word.lower()] = new_word.lower()

        if manual_translations:
            # update with manual translations
            translation.update(
                dict((key.lower(), value.lower()) for key, value in manual_translations.items())
            )

        # store data
        storage = {
            "translation": translation,
            "grammar": grammar,
            "grammar2phonemes": dict(grammar2phonemes),
            "word_length_variance": word_length_variance,
            "noun_translate": noun_translate,
            "noun_prefix": noun_prefix,
            "noun_postfix": noun_postfix,
        }
        self.db.language_storage[key] = storage

    def _translate_sub(self, match):
        """
        Replacer method called by re.sub when
        traversing the language string.

        Args:
            match (re.matchobj): Match object from regex.

        Returns:
            converted word.
        Notes:
            Assumes self.lastword and self.level is available
            on the object.

        """
        word = match.group()
        lword = len(word)

        # find out what preceeded this word
        wpos = match.start()
        preceeding = match.string[:wpos].strip()
        start_sentence = preceeding.endswith((".", "!", "?")) or not preceeding

        if len(word) <= self.level:
            # below level. Don't translate
            new_word = word
        else:
            # try to translate the word from dictionary
            new_word = self.language["translation"].get(word.lower(), "")
            if not new_word:
                # no dictionary translation. Generate one

                # make up translation on the fly. Length can
                # vary from un-translated word.
                wlen = max(
                    0,
                    lword
                    + sum(randint(-1, 1) for i in range(self.language["word_length_variance"])),
                )
                grammar = self.language["grammar"]
                if wlen not in grammar:
                    if randint(0, 1) == 0:
                        # this word has no direct translation!
                        wlen = 0
                        new_word = ""
                    else:
                        # use random word length
                        wlen = choice(list(grammar.keys()))

                if wlen:
                    structure = choice(grammar[wlen])
                    grammar2phonemes = self.language["grammar2phonemes"]
                    for match in _RE_GRAMMAR.finditer(structure):
                        # there are only four combinations: vv,cc,c,v
                        try:
                            new_word += choice(grammar2phonemes[match.group()])
                        except KeyError:
                            logger.log_trace(
                                "You need to supply at least one example of each of "
                                "the four base phonemes (c, v, cc, vv)"
                            )
                            # abort translation here
                            new_word = ""
                            break

                if word.istitle():
                    if not start_sentence:
                        # this is a noun. We miss nouns at the start of
                        # sentences this way, but it's as good as we can get
                        # with this simple analysis. Maybe the fantasy language
                        # just don't consider nouns at the beginning of
                        # sentences, who knows?
                        if not self.language.get("noun_translate", False):
                            # don't translate what we identify as proper nouns (names)
                            new_word = word

                        # add noun prefix and/or postfix
                        new_word = "{prefix}{word}{postfix}".format(
                            prefix=self.language["noun_prefix"],
                            word=new_word.capitalize(),
                            postfix=self.language["noun_postfix"],
                        )

            if len(word) > 1 and word.isupper():
                # keep LOUD words loud also when translated
                new_word = new_word.upper()

            if start_sentence:
                new_word = new_word.capitalize()

        return new_word

    def translate(self, text, level=0.0, language="default"):
        """
        Translate the text according to the given level.

        Args:
            text (str): The text to translate
            level (real): Value between 0.0 and 1.0, where
                0.0 means no obfuscation (text returned unchanged) and
                1.0 means full conversion of every word. The closer to
                1, the shorter words will be translated.
            language (str): The language key identifier.

        Returns:
            text (str): A translated string.

        """
        if level == 0.0:
            # no translation
            return text
        language = self.db.language_storage.get(language, None)
        if not language:
            return text
        self.language = language

        # configuring the translation
        self.level = int(10 * (1.0 - max(0, min(level, 1.0))))
        translation = _RE_WORD.sub(self._translate_sub, text)
        # the substitution may create too long empty spaces, remove those
        return _RE_EXTRA_CHARS.sub("", translation)


# Language access functions

_LANGUAGE_HANDLER = None


def obfuscate_language(text, level=0.0, language="default"):
    """
    Main access method for the language parser.

    Args:
        text (str): Text to obfuscate.
        level (real, optional): A value from 0.0-1.0 determining
            the level of obfuscation where 0 means no obfuscation
            (string returned unchanged) and 1.0 means the entire
            string is obfuscated.
        language (str, optional): The identifier of a language
            the system understands.

    Returns:
        translated (str): The translated text.

    """
    # initialize the language handler and cache it
    global _LANGUAGE_HANDLER
    if not _LANGUAGE_HANDLER:
        try:
            _LANGUAGE_HANDLER = LanguageHandler.objects.get(db_key="language_handler")
        except LanguageHandler.DoesNotExist:
            if not _LANGUAGE_HANDLER:
                from evennia import create_script

                _LANGUAGE_HANDLER = create_script(LanguageHandler)
    return _LANGUAGE_HANDLER.translate(text, level=level, language=language)


def add_language(**kwargs):
    """
    Access function to creating a new language. See the docstring of
    `LanguageHandler.add` for list of keyword arguments.

    """
    global _LANGUAGE_HANDLER
    if not _LANGUAGE_HANDLER:
        try:
            _LANGUAGE_HANDLER = LanguageHandler.objects.get(db_key="language_handler")
        except LanguageHandler.DoesNotExist:
            if not _LANGUAGE_HANDLER:
                from evennia import create_script

                _LANGUAGE_HANDLER = create_script(LanguageHandler)
    _LANGUAGE_HANDLER.add(**kwargs)


def available_languages():
    """
    Returns all available language keys.

    Returns:
        languages (list): List of key strings of all available
        languages.
    """
    global _LANGUAGE_HANDLER
    if not _LANGUAGE_HANDLER:
        try:
            _LANGUAGE_HANDLER = LanguageHandler.objects.get(db_key="language_handler")
        except LanguageHandler.DoesNotExist:
            if not _LANGUAGE_HANDLER:
                from evennia import create_script

                _LANGUAGE_HANDLER = create_script(LanguageHandler)
    return list(_LANGUAGE_HANDLER.attributes.get("language_storage", {}))


# -----------------------------------------------------------------------------
#
# Whisper obscuration
#
# This obsucration table is designed by obscuring certain vowels first,
# following by consonants that tend to be more audible over long distances,
# like s. Finally it does non-auditory replacements, like exclamation marks and
# capitalized letters (assumed to be spoken louder) that may still give a user
# some idea of the sentence structure. Then the  word lengths are also
# obfuscated and finally the whisper length itself.
#
# ------------------------------------------------------------------------------


_RE_WHISPER_OBSCURE = [
    re.compile(r"^$", _RE_FLAGS),  # This is a Test! #0 full whisper
    re.compile(r"[ae]", _RE_FLAGS),  # This -s - Test! #1 add uy
    re.compile(r"[aeuy]", _RE_FLAGS),  # This -s - Test! #2 add oue
    re.compile(r"[aeiouy]", _RE_FLAGS),  # Th-s -s - T-st! #3 add all consonants
    re.compile(r"[aeiouybdhjlmnpqrv]", _RE_FLAGS),  # T--s -s - T-st! #4 add hard consonants
    re.compile(r"[a-eg-rt-z]", _RE_FLAGS),  # T--s -s - T-s-! #5 add all capitals
    re.compile(r"[A-EG-RT-Za-eg-rt-z]", _RE_FLAGS),  # ---s -s - --s-! #6 add f
    re.compile(r"[A-EG-RT-Za-rt-z]", _RE_FLAGS),  # ---s -s - --s-! #7 add s
    re.compile(r"[A-EG-RT-Za-z]", _RE_FLAGS),  # ---- -- - ----! #8 add capital F
    re.compile(r"[A-RT-Za-z]", _RE_FLAGS),  # ---- -- - ----! #9 add capital S
    re.compile(r"[\w]", _RE_FLAGS),  # ---- -- - ----! #10 non-alphanumerals
    re.compile(r"[\S]", _RE_FLAGS),  # ---- -- - ----  #11 words
    re.compile(r"[\w\W]", _RE_FLAGS),  # --------------  #12 whisper length
    re.compile(r".*", _RE_FLAGS),
]  # ...             #13 (always same length)


def obfuscate_whisper(whisper, level=0.0):
    """
    Obfuscate whisper depending on a pre-calculated level
    (that may depend on distance, listening skill etc)

    Args:
        whisper (str): The whisper string to obscure. The
            entire string will be considered in the obscuration.
        level (real, optional): This is a value 0-1, where 0
            means not obscured (whisper returned unchanged) and 1
            means fully obscured.

    """
    level = min(max(0.0, level), 1.0)
    olevel = int(13.0 * level)
    if olevel == 13:
        return "..."
    else:
        return _RE_WHISPER_OBSCURE[olevel].sub("-", whisper)
