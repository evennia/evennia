"""
Unit tests for verb conjugation.

"""

from django.test import TestCase
from parameterized import parameterized

from . import conjugate, pronouns


class TestVerbConjugate(TestCase):
    """
    Test the conjugation.

    """

    @parameterized.expand(
        [
            ("have", "have"),
            ("swim", "swim"),
            ("give", "give"),
            ("given", "give"),
            ("am", "be"),
            ("doing", "do"),
            ("are", "be"),
        ]
    )
    def test_verb_infinitive(self, verb, expected):
        """
        Test the infinite-getter.
        """
        self.assertEqual(expected, conjugate.verb_infinitive(verb))

    @parameterized.expand(
        [
            ("inf", "have", "have"),
            ("inf", "swim", "swim"),
            ("inf", "give", "give"),
            ("inf", "given", "give"),
            ("inf", "am", "be"),
            ("inf", "doing", "do"),
            ("inf", "are", "be"),
            ("2sgpres", "am", "are"),
            ("3sgpres", "am", "is"),
        ]
    )
    def test_verb_conjugate(self, tense, verb, expected):
        """
        Test conjugation for different tenses.

        """
        self.assertEqual(expected, conjugate.verb_conjugate(verb, tense=tense))

    @parameterized.expand(
        [
            ("1st", "have", "have"),
            ("1st", "swim", "swim"),
            ("1st", "give", "give"),
            ("1st", "given", "give"),
            ("1st", "am", "am"),
            ("1st", "doing", "do"),
            ("1st", "are", "am"),
            ("2nd", "were", "are"),
            ("3rd", "am", "is"),
        ]
    )
    def test_verb_present(self, person, verb, expected):
        """
        Test the present.

        """
        self.assertEqual(expected, conjugate.verb_present(verb, person=person))

    @parameterized.expand(
        [
            ("have", "having"),
            ("swim", "swimming"),
            ("give", "giving"),
            ("given", "giving"),
            ("am", "being"),
            ("doing", "doing"),
            ("are", "being"),
        ]
    )
    def test_verb_present_participle(self, verb, expected):
        """
        Test the present_participle

        """
        self.assertEqual(expected, conjugate.verb_present_participle(verb))

    @parameterized.expand(
        [
            ("1st", "have", "had"),
            ("1st", "swim", "swam"),
            ("1st", "give", "gave"),
            ("1st", "given", "gave"),
            ("1st", "am", "was"),
            ("1st", "doing", "did"),
            ("1st", "are", "was"),
            ("2nd", "were", "were"),
        ]
    )
    def test_verb_past(self, person, verb, expected):
        """
        Test the past getter.

        """
        self.assertEqual(expected, conjugate.verb_past(verb, person=person))

    @parameterized.expand(
        [
            ("have", "had"),
            ("swim", "swum"),
            ("give", "given"),
            ("given", "given"),
            ("am", "been"),
            ("doing", "done"),
            ("are", "been"),
        ]
    )
    def test_verb_past_participle(self, verb, expected):
        """
        Test the past participle.

        """
        self.assertEqual(expected, conjugate.verb_past_participle(verb))

    def test_verb_get_all_tenses(self):
        """
        Test getting all tenses.

        """
        self.assertEqual(list(conjugate.verb_tenses_keys.keys()), conjugate.verb_all_tenses())

    @parameterized.expand(
        [
            ("have", "infinitive"),
            ("swim", "infinitive"),
            ("give", "infinitive"),
            ("given", "past participle"),
            ("am", "1st singular present"),
            ("doing", "present participle"),
            ("are", "2nd singular present"),
        ]
    )
    def test_verb_tense(self, verb, expected):
        """
        Test the tense retriever.

        """
        self.assertEqual(expected, conjugate.verb_tense(verb))

    @parameterized.expand(
        [
            ("inf", "have", True),
            ("inf", "swim", True),
            ("inf", "give", True),
            ("inf", "given", False),
            ("inf", "am", False),
            ("inf", "doing", False),
            ("inf", "are", False),
        ]
    )
    def test_verb_is_tense(self, tense, verb, expected):
        """
        Test the tense-checker

        """
        self.assertEqual(expected, conjugate.verb_is_tense(verb, tense))

    @parameterized.expand(
        [
            ("1st", "have", False),
            ("1st", "swim", False),
            ("1st", "give", False),
            ("1st", "given", False),
            ("1st", "am", True),
            ("1st", "doing", False),
            ("1st", "are", False),
            ("1st", "had", False),
        ]
    )
    def test_verb_is_present(self, person, verb, expected):
        """
        Test the tense-checker

        """
        self.assertEqual(expected, conjugate.verb_is_present(verb, person=person))

    @parameterized.expand(
        [
            ("have", False),
            ("swim", False),
            ("give", False),
            ("given", False),
            ("am", False),
            ("doing", True),
            ("are", False),
        ]
    )
    def test_verb_is_present_participle(self, verb, expected):
        """
        Test the tense-checker

        """
        self.assertEqual(expected, conjugate.verb_is_present_participle(verb))

    @parameterized.expand(
        [
            ("1st", "have", False),
            ("1st", "swim", False),
            ("1st", "give", False),
            ("1st", "given", False),
            ("1st", "am", False),
            ("1st", "doing", False),
            ("1st", "are", False),
            ("2nd", "were", True),
        ]
    )
    def test_verb_is_past(self, person, verb, expected):
        """
        Test the tense-checker

        """
        self.assertEqual(expected, conjugate.verb_is_past(verb, person=person))

    @parameterized.expand(
        [
            ("have", False),
            ("swimming", False),
            ("give", False),
            ("given", True),
            ("am", False),
            ("doing", False),
            ("are", False),
            ("had", False),
        ]
    )
    def test_verb_is_past_participle(self, verb, expected):
        """
        Test the tense-checker

        """
        self.assertEqual(expected, conjugate.verb_is_past_participle(verb))

    @parameterized.expand(
        [
            ("have", ("have", "has")),
            ("swimming", ("swimming", "swimming")),
            ("give", ("give", "gives")),
            ("given", ("given", "given")),
            ("am", ("are", "is")),
            ("doing", ("doing", "doing")),
            ("are", ("are", "is")),
            ("had", ("had", "had")),
            ("grin", ("grin", "grins")),
            ("smile", ("smile", "smiles")),
            ("vex", ("vex", "vexes")),
            ("thrust", ("thrust", "thrusts")),
        ]
    )
    def test_verb_actor_stance_components(self, verb, expected):
        """
        Test the tense-checker

        """
        self.assertEqual(expected, conjugate.verb_actor_stance_components(verb))


class TestPronounMapping(TestCase):
    """
    Test pronoun viewpoint mapping
    """

    @parameterized.expand(
        [
            ("you", "you", "it"),  # default 3rd is "neutral"
            ("I", "I", "it"),
            ("Me", "Me", "It"),
            ("ours", "ours", "theirs"),
            ("yourself", "yourself", "itself"),
            ("yourselves", "yourselves", "themselves"),
            ("he", "you", "he"),  # assume 2nd person
            ("her", "you", "her"),
            ("their", "your", "their"),
            ("itself", "yourself", "itself"),
            ("herself", "yourself", "herself"),
            ("themselves", "yourselves", "themselves"),
        ]
    )
    def test_default_mapping(self, pronoun, expected_1st_or_2nd_person, expected_3rd_person):
        """
        Test the pronoun mapper.

        """
        received_1st_or_2nd_person, received_3rd_person = pronouns.pronoun_to_viewpoints(pronoun)

        self.assertEqual(expected_1st_or_2nd_person, received_1st_or_2nd_person)
        self.assertEqual(expected_3rd_person, received_3rd_person)

    @parameterized.expand(
        [
            ("you", "m", "you", "he"),
            ("you", "f op", "you", "her"),
            ("you", "p op", "you", "them"),
            ("I", "m", "I", "he"),
            ("Me", "n", "Me", "It"),
            ("your", "p", "your", "their"),
            ("yourself", "m", "yourself", "himself"),
            ("yourself", "f", "yourself", "herself"),
            ("yourselves", "", "yourselves", "themselves"),
            ("he", "1", "I", "he"),
            ("he", "1 p", "we", "he"),  # royal we
            ("we", "m", "we", "he"),  # royal we, other way
            ("her", "p", "you", "her"),
            ("her", "pa", "your", "her"),
            ("their", "ma", "your", "their"),
        ]
    )
    def test_mapping_with_options(
        self, pronoun, options, expected_1st_or_2nd_person, expected_3rd_person
    ):
        """
        Test the pronoun mapper.

        """
        received_1st_or_2nd_person, received_3rd_person = pronouns.pronoun_to_viewpoints(
            pronoun, options
        )
        self.assertEqual(expected_1st_or_2nd_person, received_1st_or_2nd_person)
        self.assertEqual(expected_3rd_person, received_3rd_person)

    @parameterized.expand(
        [
            ("you", "p", "you", "they"),
            ("I", "p", "I", "they"),
            ("Me", "p", "Me", "Them"),
            ("your", "p", "your", "their"),
            ("they", "1 p", "we", "they"),
            ("they", "", "you", "they"),
            ("yourself", "p", "yourself", "themselves"),
            ("myself", "p", "myself", "themselves"),
        ]
    )
    def test_colloquial_plurals(
        self, pronoun, options, expected_1st_or_2nd_person, expected_3rd_person
    ):
        """
        The use of this module by the funcparser expects a default person-pronoun
        of the neutral "they", which is categorized here by the plural.

        """
        received_1st_or_2nd_person, received_3rd_person = pronouns.pronoun_to_viewpoints(
            pronoun, options
        )

        self.assertEqual(expected_1st_or_2nd_person, received_1st_or_2nd_person)
        self.assertEqual(expected_3rd_person, received_3rd_person)
