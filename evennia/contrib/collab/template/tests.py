"""
Tests for the collab templating system.
"""
from ddt import ddt, unpack, data
from django.test import override_settings
from evennia.contrib.collab.perms import set_owner
from evennia.contrib.collab.template.core import evtemplate
from evennia.contrib.collab.test_base import CollabTest, collab_overrides
from mock import patch


class Unsupported(object):
    def __repr__(self):
        return "<unsupported>"


@ddt
@override_settings(**collab_overrides)
class TemplateTestCase(CollabTest):
    def test_unmodified_string(self):
        self.assertEqual(
            evtemplate("test string", run_as=self.char1, me=self.char1, this=self.char1),
            "test string"
        )

    @patch('evennia.contrib.collab.template.core.logger')
    def test_no_run_as(self, mock_logger):
        self.assertEqual(
            evtemplate("{% pro %}{o{% endpro %}", me=self.char1, this=self.char1),
            "{% pro %}{o{% endpro %}"
        )
        mock_logger.info.assert_called_with("Refused to render template without run_as set. Returning raw string.")

    def test_no_me(self):
        self.assertRaises(ValueError, evtemplate, "test string", this=self.char1, run_as=self.char1)

    def test_no_this(self):
        self.assertRaises(ValueError, evtemplate, "test_string", run_as=self.char1, me=self.char1)

    @unpack
    @data(
        ('male', "He had his thoughts with him, and they were his."),
        ('female', "She had her thoughts with her, and they were hers."),
        ('neutral', "They had their thoughts with them, and they were theirs."),
        ('hermaphrodite', "Shi had hir thoughts with hir, and they were hirs.")
    )
    def test_pronoun_substitution_default(self, gender, output):
        self.char1.usrdb.gender = gender
        self.char1.usrdb.custom_gender_map = {
            'neutral': {
                's': 'they',
                'p': 'their',
                'o': 'them',
                'a': 'theirs',
            },
            'hermaphrodite': {
                's': 'shi',
                'p': 'hir',
                'o': 'hir',
                'a': 'hirs',
            }
        }
        self.assertEqual(
            evtemplate(
                "{% pro %}|S had |p thoughts with |o, and they were |a.{% endpro %}", me=self.char1,
                this=self.obj1, run_as=self.obj1,
            ),
            output
        )

    def test_pronoun_substitution_variable(self):
        self.char1.usrdb.gender = 'male'
        self.char2.usrdb.gender = 'female'
        self.assertEqual(
            evtemplate(
                "{% pro you %}|S had |p thoughts with |o, and they were |a.{% endpro %}", me=self.char1,
                this=self.obj1, run_as=self.obj1, context={'you': self.char2}
            ),
            "She had her thoughts with her, and they were hers."
        )

    def test_store_attribute(self):
        set_owner(self.char1, self.obj1)
        evtemplate(
            "{{ store(this, 'test', 'value') }}", me=self.char1, this=self.obj1, run_as=self.char1,
        )
        self.assertEqual(self.obj1.usrattributes.get('test'), 'value')
        self.assertEqual(self.obj1.usrdb.test, 'value')

    def test_fetch_attribute(self):
        set_owner(self.char1, self.obj1)
        self.obj1.usrdb.stuff = 'thing'
        self.assertEqual(
            evtemplate(
                "{{ fetch(this, 'stuff') }}", me=self.char1, this=self.obj1, run_as=self.char1,
            ),
            "thing"
        )

    def test_permissioned_read(self):
        """
        Make sure a non-owner can read a readable attribute.
        """
        set_owner(self.char1, self.obj1)
        self.obj1.usrdb.stuff = 'thing'
        self.assertEqual(
            evtemplate(
                "{{ fetch(this, 'stuff') }}", me=self.char2, this=self.obj1, run_as=self.char2,
            ),
            "thing"
        )

    def test_unpermissioned_read(self):
        """
        Make sure a non-owner can't read an unreadable attribute.
        """
        self.obj1.admdb.stuff = 'thing'
        self.assertEqual(
            evtemplate(
                "{{ fetch(this, 'adm_stuff') }}", me=self.char2, this=self.obj1, run_as=self.char2,
            ),
            "Error when executing template. SecurityError: Char2 does not have read "
            "access to property 'adm_stuff' on Obj"
        )

    def test_permissioned_write(self):
        """
        Make sure a non-owner can write to a writable attribute.
        """
        self.assertEqual(
            evtemplate(
                "{{ store(this, 'pub_stuff', 'things') }}", me=self.char2, this=self.obj1, run_as=self.char2,
            ),
            ""
        )
        self.assertEqual(self.obj1.pubdb.stuff, 'things')

    def test_unpermissioned_write(self):
        """
        Make sure a non-owner can't write to a non-writable attribute.
        """
        self.assertEqual(
            evtemplate(
                "{{ store(this, 'adm_stuff', 'things') }}", me=self.char2, this=self.obj1, run_as=self.char2,
            ),
            "Error when executing template. SecurityError: Char2 does not have write "
            "access to property 'adm_stuff' on Obj"
        )
        self.assertIsNone(self.obj1.admdb.stuff)

    def test_owned_no_read(self):
        """
        Make sure owners can't read above their permission levels.
        """
        set_owner(self.char2, self.obj1)
        self.obj1.admhdb.stuff = 'thing'
        self.assertEqual(
            evtemplate(
                "{{ fetch(this, 'admh_stuff') }}", me=self.char2, this=self.obj1, run_as=self.char2,
            ),
            "Error when executing template. SecurityError: Char2 does not have read "
            "access to property 'admh_stuff' on Obj"
        )

    def test_owned_no_write(self):
        """
        Make sure owners can't write above their permission levels.
        """
        set_owner(self.char2, self.obj1)
        self.assertEqual(
            evtemplate(
                "{{ store(this, 'adm_stuff', 'thing') }}", me=self.char2, this=self.obj1, run_as=self.char2,
            ),
            "Error when executing template. SecurityError: Char2 does not have write "
            "access to property 'adm_stuff' on Obj"
        )
        self.assertIsNone(self.obj1.admdb.stuff)

    def test_include(self):
        self.obj1.usrdb.test = 'This is a test.'
        self.obj1.usrdb.stuff = "{{ fetch(this, 'test') }}"
        self.assertEqual(
            evtemplate(
                "{% include fetch(this, 'stuff') %}", me=self.char2, this=self.obj1, run_as=self.char2,
            ),
            "This is a test."
        )

    def test_read_unsupported(self):
        self.obj1.usrdb.test = Unsupported()
        self.assertEqual(
            evtemplate(
                "{{ fetch(this, 'test') }}", me=self.char2, this=self.obj1, run_as=self.char2,
            ),
            "Error when executing template. SecurityError: 'test' on Obj contains "
            "data which cannot be securely sandboxed."
        )

    def test_write_unsupported(self):
        set_owner(self.char2, self.obj1)
        self.assertEqual(
            evtemplate(
                "{{ store(this, 'test', extra) }}", me=self.char2, this=self.obj1, run_as=self.char2,
                extra=Unsupported()
            ),
            "Error when executing template. SecurityError: <unsupported> contains data "
            "which cannot be securely sandboxed."
        )

    def handle_graceful_none_template(self):
        self.assertEqual(
            evtemplate(
                "{% include fetch(this, 'test') %}", me=self.char2, this=self.obj1, run_as=self.char2,
                extra=Unsupported()
            ),
            "Include error: Attempted to include a null value. Check to make sure your include "
            "statement contains a template string."
        )

    def test_graceful_exception(self):
        self.assertEqual(
            evtemplate(
                "{% include 2 %}", me=self.char2, this=self.obj1, run_as=self.char2,
                extra=Unsupported()
            ),
            "Error when executing template on line 1. TypeError: 'int' object is not iterable"
        )
