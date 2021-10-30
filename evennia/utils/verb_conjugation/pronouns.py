"""
English pronoun mapping between 1st/2nd person and 3rd person perspective (and vice-versa).

This file is released under the Evennia regular BSD License.
(Griatch 2021)

Pronouns are words you use instead of a proper name, such as 'him', 'herself', 'theirs' etc. These
look different depending on who sees the outgoing string. This mapping maps between 1st/2nd case and
the 3rd person case and back. In some cases, the mapping is not unique; it is assumed the system can
differentiate between the options in some other way.


====================  =======  ========  ==========  ==========  ===========
viewpoint/pronouns    Subject  Object    Possessive  Possessive  Reflexive
                      Pronoun  Pronoun   Adjective   Pronoun     Pronoun
====================  =======  ========  ==========  ==========  ===========
1st person              I        me        my         mine       myself
1st person plural       we       us        our        ours       ourselves
2nd person              you      you       your       yours      yourself
2nd person plural       you      you       your       yours      yourselves

3rd person male         he       him       his        his        himself
3rd person female       she      her       her        hers       herself
3rd person neutral      it       it        its        theirs*    itself
3rd person plural       they     them      their      theirs     themselves
====================  =======  ========  ==========  ==========  ===========

> `*`) Not formally used, we use `theirs` here as a filler.

"""
from evennia.utils.utils import copy_word_case

DEFAULT_PRONOUN_TYPE = "object_pronoun"
DEFAULT_VIEWPOINT = "2nd person"
DEFAULT_GENDER = "neutral"

PRONOUN_MAPPING = {
    # 1st/2nd person -> 3rd person mappings
    "I": {
        "subject pronoun": {
            "3rd person": {
                "male": "he",
                "female": "she",
                "neutral": "it"
            }
        }
    },
    "me": {
        "object pronoun": {
            "3rd person": {
                "male": "him",
                "female": "her",
                "neutral": "it"
            }
        }
    },
    "my": {
        "possessive adjective": {
            "3rd person": {
                "male": "his",
                "female": "her",
                "neutral": "its"
            }
        }
    },
    "mine": {
        "possessive pronoun": {
            "3rd person": {
                "male": "his",
                "female": "hers",
                "neutral": "theirs",  # colloqial,
            }
        }
    },
    "myself": {
        "reflexive_pronoun": {
            "3rd person": {
                "male": "himself",
                "female": "herself",
                "neutral": "itself",
                "plural": "themselves",
            }
        }
    },
    "you": {
        "subject pronoun": {
            "3rd person": {
                "male": "he",
                "female": "she",
                "neutral": "it",
                "plural": "they",
            }
        },
        "object pronoun": {
            "3rd person": {
                "male": "him",
                "female": "her",
                "neutral": "it",
                "plural": "them",
            }
        }
    },
    "your": {
        "possessive adjective": {
            "3rd person": {
                "male": "his",
                "female": "her",
                "neutral": "its",
                "plural": "their",
            }
        }
    },
    "yours": {
        "possessive pronoun": {
            "3rd person": {
                "male": "his",
                "female": "hers",
                "neutral": "theirs",  # colloqial
                "plural": "theirs"
            }
        }
    },
    "yourself": {
        "reflexive_pronoun": {
            "3rd person": {
                "male": "himself",
                "female": "herself",
                "neutral": "itself",
            }
        }
    },
    "we": {
        "subject pronoun": {
            "3rd person": {
                "plural": "they"
            }
        }
    },
    "us": {
        "object pronoun": {
            "3rd person": {
                "plural": "them"
            }
        }
    },
    "our": {
        "possessive adjective": {
            "3rd person": {
                "plural": "their"
            }
        }
    },
    "ours": {
        "possessive pronoun": {
            "3rd person": {
                "plural": "theirs"
            }
        }
    },
    "ourselves": {
        "reflexive pronoun": {
            "3rd person": {
                "plural": "themselves"
            }
        }
    },
    "ours": {
        "possessive pronoun": {
            "3rd person": {
                "plural": "theirs"
            }
        }
    },
    "ourselves": {
        "reflexive pronoun": {
            "3rd person": {
                "plural": "themselves"
            }
        }
    },
    "yourselves": {
        "reflexive_pronoun": {
            "3rd person": {
                "plural": "themselves"
            }
        }
    },
    # 3rd person to 1st/second person mappings
    "he": {
        "subject pronoun": {
            "1st person": {
                "neutral": "I",
                "plural": "we"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "you",
                "plural": "you"  # pluralis majestatis
            }
        }
    },
    "him": {
        "object pronoun": {
            "1st person": {
                "neutral": "me",
                "plural": "us"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "you",
                "plural": "you"  # pluralis majestatis
            },
        }
    },
    "his": {
        "possessive adjective": {
            "1st person": {
                "neutral": "my",
                "plural": "our"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "your",
                "plural": "your"  # pluralis majestatis
            }
        },
        "possessive pronoun": {
            "1st person": {
                "neutral": "mine",
                "plural": "ours"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "yours",
                "plural": "yours"  # pluralis majestatis
            }
        }
    },
    "himself": {
        "reflexive pronoun": {
            "1st person": {
                "neutral": "myself",
                "plural": "ourselves"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "yours",
                "plural": "yours"  # pluralis majestatis
            }
        },
    },
    "she": {
        "subject pronoun": {
            "1st person": {
                "neutral": "I",
                "plural": "you"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "you",
                "plural": "we"  # pluralis majestatis
            }
        }
    },
    "her": {
        "object pronoun": {
            "1st person": {
                "neutral": "me",
                "plural": "us"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "you",
                "plural": "you"  # pluralis majestatis
            }
        },
        "possessive adjective": {
            "1st person": {
                "neutral": "my",
                "plural": "our"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "your",
                "plural": "your"  # pluralis majestatis
            }
        },
    },
    "hers": {
        "possessive pronoun": {
            "1st person": {
                "neutral": "mine",
                "plural": "ours"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "yours",
                "plural": "yours"  # pluralis majestatis
            }
        }
    },
    "herself": {
        "reflexive pronoun": {
            "1st person": {
                "neutral": "myself",
                "plural": "ourselves"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "yourself",
                "plural": "yourselves"  # pluralis majestatis
            }
        },
    },
    "it": {
        "subject pronoun": {
            "1st person": {
                "neutral": "I",
                "plural": "we"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "you",
                "plural": "you"  # pluralis majestatis
            }
        },
        "object pronoun": {
            "1st person": {
                "neutral": "me",
                "plural": "us"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "you",
                "plural": "you"  # pluralis majestatis
            }
        }
    },
    "its": {
        "possessive adjective": {
            "1st person": {
                "neutral": "my",
                "plural": "our"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "your",
                "plural": "your"  # pluralis majestatis
            }
        }
    },
    "theirs": {
        "possessive pronoun": {
            "1st person": {
                "neutral": "mine",
                "plural": "ours"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "yours",
                "plural": "yours"  # pluralis majestatis
            }
        }
    },
    "itself": {
        "reflexive pronoun": {
            "1st person": {
                "neutral": "myself",
                "plural": "ourselves"  # pluralis majestatis
            },
            "2nd person": {
                "neutral": "yourself",
                "plural": "yourselves"  # pluralis majestatis
            }
        },
    },
    "they": {
        "subject pronoun": {
            "1st person": {
                "plural": "we",
            },
            "2nd person": {
                "plural": "you",
            }
        }
    },
    "them": {
        "object pronoun": {
            "1st person": {
                "plural": "us",
            },
            "2nd person": {
                "plural": "you",
            }
        }
    },
    "their": {
        "possessive adjective": {
            "1st person": {
                "plural": "our",
            },
            "2nd person": {
                "plural": "your",
            }
        }
    },
    "themselves": {
        "reflexive pronoun": {
            "1st person": {
                "plural": "ourselves",
            },
            "2nd person": {
                "plural": "yourselves",
            }
        }
    }
}


ALIASES = {
    "m": "male",
    "f": "female",
    "n": "neutral",
    "p": "plural",
    "1st": "1st person",
    "2nd": "2nd person",
    "3rd": "3rd person",
    "1": "1st person",
    "2": "2nd person",
    "3": "3rd person",
    "s": "subject pronoun",
    "sp": "subject pronoun",
    "subject": "subject pronoun",
    "op": "object pronoun",
    "object": "object pronoun",
    "pa": "possessive adjective",
    "pp": "possessive pronoun",
}

PRONOUN_TYPES = ["subject pronoun", "object pronoun", "possessive adjective",
                 "possessive pronoun", "reflexive pronoun"]
VIEWPOINTS = ["1st person", "2nd person", "3rd person"]
GENDERS = ["male", "female", "neutral", "plural"]  # including plural as a gender for simplicity


def pronoun_to_viewpoints(pronoun,
                options=None, pronoun_type="object_pronoun",
                gender="neutral", viewpoint="2nd person"):
    """
    Access function for determining the forms of a pronount from different viewpoints.

    Args:
        pronoun (str): A valid English pronoun, such as 'you', 'his', 'themselves' etc.
        options (str or list, optional): A list or space-separated string of options to help
            the engine when there is no unique mapping to use. This could for example
            be "2nd female" (alias 'f') or "possessive adjective" (alias 'pa' or 'a').
        pronoun_type (str, optional): An explicit object pronoun to separate cases where
            there is no unique mapping. Pronoun types defined in `options` take precedence.
            Values are

            - `subject pronoun`/`subject`/`sp` (I, you, he, they)
            - `object pronoun`/`object/`/`op`  (me, you, him, them)
            - `possessive adjective`/`adjective`/`pa` (my, your, his, their)
            - `possessive pronoun`/`pronoun`/`pp`  (mine, yours, his, theirs)

        gender (str, optional): Specific gender to use (plural counts a gender for this purpose).
            A gender specified in `options` takes precedence. Values and aliases are:

            - `male`/`m`
            - `female`/`f`
            - `neutral`/`n`
            - `plural`/`p`

        viewpoint (str, optional): A specified viewpoint of the one talking, to use
            when there is no unique mapping. A viewpoint given in `options` take
            precedence. Values and aliases are:

            - `1st person`/`1st`/`1`
            - `2nd person`/`2nd`/`2`
            - `3rd person`/`3rd`/`3`

    Returns:
        tuple: A tuple `(1st/2nd_person_pronoun, 3rd_person_pronoun)` to show to the one sending the
        string and others respectively. If pronoun is invalid, the word is returned verbatim.

    Note:
        The capitalization of the original word will be retained.

    """
    if not pronoun:
        return pronoun

    pronoun_lower = "I" if pronoun == "I" else pronoun.lower()

    if pronoun_lower not in PRONOUN_MAPPING:
        return pronoun

    # differentiators

    if pronoun_type not in PRONOUN_TYPES:
        pronoun_type = DEFAULT_PRONOUN_TYPE
    if viewpoint not in VIEWPOINTS:
        viewpoint = DEFAULT_VIEWPOINT
    if gender not in GENDERS:
        gender = DEFAULT_GENDER

    if options:
        # option string/list will override the kwargs differentiators given
        if isinstance(options, str):
            options = options.split()
        options = [str(part).strip().lower() for part in options]
        options = [ALIASES.get(opt, opt) for opt in options]

        for opt in options:
            if opt in PRONOUN_TYPES:
                pronoun_type = opt
            elif opt in VIEWPOINTS:
                viewpoint = opt
            elif opt in GENDERS:
                gender = opt

    # step down into the mapping, using differentiators as needed
    pronoun_types = PRONOUN_MAPPING[pronoun_lower]
    # this has one or more pronoun-types
    if len(pronoun_types) == 1:
        pronoun_type, viewpoints = next(iter(pronoun_types.items()))
    elif pronoun_type in pronoun_types:
        viewpoints = pronoun_types[pronoun_type]
    elif DEFAULT_PRONOUN_TYPE in pronoun_types:
        pronoun_type = DEFAULT_PRONOUN_TYPE
        viewpoints = pronoun_types[pronoun_type]
    else:
        # not enough info - grab the first of the mappings
        pronoun_type, viewpoints = next(iter(pronoun_types.items()))

    # we have one or more viewpoints at this point
    if len(viewpoints) == 1:
        viewpoint, genders = next(iter(viewpoints.items()))
    elif viewpoint in viewpoints:
        genders = viewpoints[viewpoint]
    elif DEFAULT_VIEWPOINT in viewpoints:
        viewpoint = DEFAULT_VIEWPOINT
        genders = viewpoints[viewpoint]
    else:
        # not enough info - grab first of mappings
        viewpoint, genders = next(iter(viewpoints.items()))

    # we have one or more possible genders (including plural forms)
    if len(genders) == 1:
        gender, mapped_pronoun = next(iter(genders.items()))
    elif gender in genders:
        mapped_pronoun = genders[gender]
    elif DEFAULT_GENDER in genders:
        gender = DEFAULT_GENDER
        mapped_pronoun = genders[gender]
    else:
        # not enough info - grab first mapping
        gender, mapped_pronoun = next(iter(genders.items()))

    # keep the same capitalization as the original
    if pronoun != "I":
        # don't remap I, since this is always capitalized.
        mapped_pronoun = copy_word_case(pronoun, mapped_pronoun)
    if mapped_pronoun == "i":
        mapped_pronoun = mapped_pronoun.upper()

    if viewpoint == "3rd person":
        # the remapped viewpoing is in 3rd person, meaning the ingoing viewpoing
        # must have been 1st or 2nd person.
        return pronoun, mapped_pronoun
    else:
        # the remapped viewpoint is 1st or 2nd person, so ingoing must have been
        # in 3rd person form.
        return mapped_pronoun, pronoun
