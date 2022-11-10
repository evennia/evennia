"""
Resources for indexing help entries and for splitting help entries into
sub-categories.

This is used primarily by the default `help` command.

"""
import re

from django.conf import settings

# these are words that Lunr normally ignores but which we want to find
# since we use them (e.g. as command names).
# Lunr's default ignore-word list is found here:
# https://github.com/yeraydiazdiaz/lunr.py/blob/master/lunr/stop_word_filter.py
_LUNR_STOP_WORD_FILTER_EXCEPTIONS = [
    "about",
    "might",
    "get",
    "who",
    "say",
] + settings.LUNR_STOP_WORD_FILTER_EXCEPTIONS


_LUNR = None
_LUNR_EXCEPTION = None

_LUNR_GET_BUILDER = None
_LUNR_BUILDER_PIPELINE = None

_RE_HELP_SUBTOPICS_START = re.compile(r"^\s*?#\s*?subtopics\s*?$", re.I + re.M)
_RE_HELP_SUBTOPIC_SPLIT = re.compile(r"^\s*?(\#{2,6}\s*?\w+?[a-z0-9 \-\?!,\.]*?)$", re.M + re.I)
_RE_HELP_SUBTOPIC_PARSE = re.compile(r"^(?P<nesting>\#{2,6})\s*?(?P<name>.*?)$", re.I + re.M)

MAX_SUBTOPIC_NESTING = 5


def help_search_with_index(query, candidate_entries, suggestion_maxnum=5, fields=None):
    """
    Lunr-powered fast index search and suggestion wrapper. See https://lunrjs.com/.

    Args:
        query (str): The query to search for.
        candidate_entries (list): This is the body of possible entities to search. Each
            must have a property `.search_index_entry` that returns a dict with all
            keys in the `fields` arg.
        suggestion_maxnum (int): How many matches to allow at most in a multi-match.
        fields (list, optional): A list of Lunr field mappings
            ``{"field_name": str, "boost": int}``. See the Lunr documentation
            for more details. The field name must exist in the dicts returned
            by `.search_index_entry` of the candidates. If not given, a default setup
            is used, prefering keys > aliases > category > tags.
    Returns:
        tuple: A tuple (matches, suggestions), each a list, where the `suggestion_maxnum` limits
            how many suggestions are included.

    """
    global _LUNR, _LUNR_EXCEPTION, _LUNR_BUILDER_PIPELINE, _LUNR_GET_BUILDER
    if not _LUNR:
        # we have to delay-load lunr because it messes with logging if it's imported
        # before twisted's logging has been set up
        from lunr import get_default_builder as _LUNR_GET_BUILDER
        from lunr import lunr as _LUNR
        from lunr import stop_word_filter
        from lunr.exceptions import QueryParseError as _LUNR_EXCEPTION
        from lunr.stemmer import stemmer

        # from lunr.trimmer import trimmer
        # pre-create a lunr index-builder pipeline where we've removed some of
        # the stop-words from the default in lunr.

        stop_words = stop_word_filter.WORDS

        for ignore_word in _LUNR_STOP_WORD_FILTER_EXCEPTIONS:
            try:
                stop_words.remove(ignore_word)
            except ValueError:
                pass

        custom_stop_words_filter = stop_word_filter.generate_stop_word_filter(stop_words)
        # _LUNR_BUILDER_PIPELINE = (trimmer, custom_stop_words_filter, stemmer)
        _LUNR_BUILDER_PIPELINE = (custom_stop_words_filter, stemmer)

    indx = [cnd.search_index_entry for cnd in candidate_entries]
    mapping = {indx[ix]["key"]: cand for ix, cand in enumerate(candidate_entries)}

    if not fields:
        fields = [
            {"field_name": "key", "boost": 10},
            {"field_name": "aliases", "boost": 9},
            {"field_name": "category", "boost": 8},
            {"field_name": "tags", "boost": 5},
        ]

    # build the search index
    builder = _LUNR_GET_BUILDER()
    builder.pipeline.reset()
    builder.pipeline.add(*_LUNR_BUILDER_PIPELINE)

    search_index = _LUNR(ref="key", fields=fields, documents=indx, builder=builder)

    try:
        matches = search_index.search(query)[:suggestion_maxnum]
    except _LUNR_EXCEPTION:
        # this is a user-input problem
        matches = []

    # matches (objs), suggestions (strs)
    return (
        [mapping[match["ref"]] for match in matches],
        [str(match["ref"]) for match in matches],  # + f" (score {match['score']})")   # good debug
    )


def parse_entry_for_subcategories(entry):
    """
    Parse a command docstring for special sub-category blocks:

    Args:
        entry (str): A help entry to parse

    Returns:
        dict: The dict is a mapping that splits the entry into subcategories. This
            will always hold a key `None` for the main help entry and
            zero or more keys holding the subcategories. Each is itself
            a dict with a key `None` for the main text of that subcategory
            followed by any sub-sub-categories down to a max-depth of 5.

    Example:
    ::

        '''
        Main topic text

        # SUBTOPICS

        ## foo

        A subcategory of the main entry, accessible as `help topic foo`
        (or using /, like `help topic/foo`)

        ## bar

        Another subcategory, accessed as `help topic bar`
        (or `help topic/bar`)

        ### moo

        A subcategory of bar, accessed as `help bar moo`
        (or `help bar/moo`)

        #### dum

        A subcategory of moo, accessed `help bar moo dum`
        (or `help bar/moo/dum`)

        '''

    This will result in this returned entry structure:
    ::

        {
           None: "Main topic text":
           "foo": {
                None: "main topic/foo text"
           },
           "bar": {
                None: "Main topic/bar text",
                "moo": {
                    None: "topic/bar/moo text"
                    "dum": {
                        None: "topic/bar/moo/dum text"
                    }
                }
           }
        }

    """
    topic, *subtopics = _RE_HELP_SUBTOPICS_START.split(entry, maxsplit=1)
    structure = {None: topic.strip("\n")}

    if subtopics:
        subtopics = subtopics[0]
    else:
        return structure

    keypath = []
    current_nesting = 0
    subtopic = None

    # from evennia import set_trace;set_trace()
    for part in _RE_HELP_SUBTOPIC_SPLIT.split(subtopics.strip()):

        subtopic_match = _RE_HELP_SUBTOPIC_PARSE.match(part.strip())
        if subtopic_match:
            # a new sub(-sub..) category starts.
            mdict = subtopic_match.groupdict()
            subtopic = mdict["name"].lower().strip()
            new_nesting = len(mdict["nesting"]) - 1

            if new_nesting > MAX_SUBTOPIC_NESTING:
                raise RuntimeError(
                    f"Can have max {MAX_SUBTOPIC_NESTING} levels of nested help subtopics."
                )

            nestdiff = new_nesting - current_nesting
            if nestdiff < 0:
                # jumping back up in nesting
                for _ in range(abs(nestdiff) + 1):
                    try:
                        keypath.pop()
                    except IndexError:
                        pass
            elif nestdiff == 0:
                # don't add a deeper nesting but replace the current
                try:
                    keypath.pop()
                except IndexError:
                    pass
            keypath.append(subtopic)
            current_nesting = new_nesting
        else:
            # an entry belonging to a subtopic - find the nested location
            dct = structure
            if not keypath and subtopic is not None:
                structure[subtopic] = part
            else:
                for key in keypath:
                    if key in dct:
                        dct = dct[key]
                    else:
                        dct[key] = {None: part}
    return structure
