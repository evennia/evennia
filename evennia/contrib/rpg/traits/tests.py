#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit test module for Trait classes.

"""

from copy import copy

from anything import Something
from mock import MagicMock, patch

from evennia.objects.objects import DefaultCharacter
from evennia.utils.test_resources import BaseEvenniaTestCase, EvenniaTest

from . import traits


class _MockObj:
    def __init__(self):
        self.attributes = MagicMock()
        self.attributes.get = self.get
        self.attributes.add = self.add
        self.dbstore = {}
        self.category = "traits"

    def get(self, key, category=None):
        assert category == self.category
        return self.dbstore.get(key)

    def add(self, key, value, category=None):
        assert category == self.category
        self.dbstore[key] = value


# we want to test the base traits too
_TEST_TRAIT_CLASS_PATHS = [
    "evennia.contrib.rpg.traits.Trait",
    "evennia.contrib.rpg.traits.StaticTrait",
    "evennia.contrib.rpg.traits.CounterTrait",
    "evennia.contrib.rpg.traits.GaugeTrait",
]


class _TraitHandlerBase(BaseEvenniaTestCase):
    "Base for trait tests"

    @patch("evennia.contrib.rpg.traits.traits._TRAIT_CLASS_PATHS", new=_TEST_TRAIT_CLASS_PATHS)
    def setUp(self):
        self.obj = _MockObj()
        self.traithandler = traits.TraitHandler(self.obj)
        self.obj.traits = self.traithandler

    def _get_dbstore(self, key):
        return self.obj.dbstore["traits"][key]


class TraitHandlerTest(_TraitHandlerBase):
    """Testing for TraitHandler"""

    def setUp(self):
        super().setUp()
        self.traithandler.add("test1", name="Test1", trait_type="trait")
        self.traithandler.add(
            "test2",
            name="Test2",
            trait_type="trait",
            value=["foo", {"1": [1, 2, 3]}, 4],
        )

    def test_add_trait(self):
        self.assertEqual(
            self._get_dbstore("test1"),
            {
                "name": "Test1",
                "trait_type": "trait",
                "value": None,
            },
        )
        self.assertEqual(
            self._get_dbstore("test2"),
            {
                "name": "Test2",
                "trait_type": "trait",
                "value": ["foo", {"1": [1, 2, 3]}, 4],
            },
        )
        self.assertEqual(len(self.traithandler), 2)

    def test_cache(self):
        """
        Cache should not be set until first get
        """
        self.assertEqual(len(self.traithandler._cache), 0)
        self.traithandler.all()  # does not affect cache
        self.assertEqual(len(self.traithandler._cache), 0)
        self.traithandler.test1
        self.assertEqual(len(self.traithandler._cache), 1)
        self.traithandler.test2
        self.assertEqual(len(self.traithandler._cache), 2)

    def test_setting(self):
        "Don't allow setting stuff on traithandler"
        with self.assertRaises(traits.TraitException):
            self.traithandler.foo = "bar"
        with self.assertRaises(traits.TraitException):
            self.traithandler["foo"] = "bar"
        with self.assertRaises(traits.TraitException):
            self.traithandler.test1 = "foo"

    def test_getting(self):
        "Test we are getting data from the dbstore"
        self.assertEqual(
            self.traithandler.test1._data, {"name": "Test1", "trait_type": "trait", "value": None}
        )
        self.assertEqual(self.traithandler._cache, Something)
        self.assertEqual(
            self.traithandler.test2._data,
            {"name": "Test2", "trait_type": "trait", "value": ["foo", {"1": [1, 2, 3]}, 4]},
        )
        self.assertEqual(self.traithandler._cache, Something)
        self.assertFalse(self.traithandler.get("foo"))
        self.assertFalse(self.traithandler.bar)

    def test_all(self):
        "Test all method"
        self.assertEqual(self.traithandler.all(), ["test1", "test2"])

    def test_remove(self):
        "Test remove method"
        self.traithandler.remove("test2")
        self.assertEqual(len(self.traithandler), 1)
        self.assertTrue(bool(self.traithandler.get("test1")))  # this populates cache
        self.assertEqual(len(self.traithandler._cache), 1)
        with self.assertRaises(traits.TraitException):
            self.traithandler.remove("foo")

    def test_clear(self):
        "Test clear method"
        self.traithandler.clear()
        self.assertEqual(len(self.traithandler), 0)

    def test_trait_db_connection(self):
        "Test that updating a trait property actually updates value in db"
        trait = self.traithandler.test1
        self.assertEqual(trait.value, None)
        trait.value = 10
        self.assertEqual(trait.value, 10)
        self.assertEqual(self.obj.attributes.get("traits", category="traits")["test1"]["value"], 10)
        trait.value = 20
        self.assertEqual(trait.value, 20)
        self.assertEqual(self.obj.attributes.get("traits", category="traits")["test1"]["value"], 20)
        del trait.value
        self.assertEqual(
            self.obj.attributes.get("traits", category="traits")["test1"]["value"], None
        )


class TestTrait(_TraitHandlerBase):
    """
    Test the base Trait class
    """

    def setUp(self):
        super().setUp()
        self.traithandler.add(
            "test1",
            name="Test1",
            trait_type="trait",
            value="value",
            extra_val1="xvalue1",
            extra_val2="xvalue2",
        )
        self.trait = self.traithandler.get("test1")

    def test_init(self):
        self.assertEqual(
            self.trait._data,
            {
                "name": "Test1",
                "trait_type": "trait",
                "value": "value",
                "extra_val1": "xvalue1",
                "extra_val2": "xvalue2",
            },
        )

    def test_validate_input__valid(self):
        """Test valid validation input"""
        # all data supplied, and extras
        dat = {"name": "Test", "trait_type": "trait", "value": 10, "extra_val": 1000}
        expected = copy(dat)  # we must break link or return === dat always
        self.assertEqual(expected, traits.Trait.validate_input(traits.Trait, dat))

        # don't supply value, should get default
        dat = {
            "name": "Test",
            "trait_type": "trait",
            # missing value
            "extra_val": 1000,
        }
        expected = copy(dat)
        expected["value"] = traits.Trait.default_keys["value"]
        self.assertEqual(expected, traits.Trait.validate_input(traits.Trait, dat))

        # make sure extra values are cleaned if trait accepts no extras
        dat = {
            "name": "Test",
            "trait_type": "trait",
            "value": 10,
            "extra_val1": 1000,
            "extra_val2": "xvalue",
        }
        expected = copy(dat)
        expected.pop("extra_val1")
        expected.pop("extra_val2")
        with patch.object(traits.Trait, "allow_extra_properties", False):
            self.assertEqual(expected, traits.Trait.validate_input(traits.Trait, dat))

    def test_validate_input__fail(self):
        """Test failing validation"""
        dat = {
            # missing name
            "trait_type": "trait",
            "value": 10,
            "extra_val": 1000,
        }
        with self.assertRaises(traits.TraitException):
            traits.Trait.validate_input(traits.Trait, dat)

        # make value a required key
        mock_default_keys = {"value": traits.MandatoryTraitKey}
        with patch.object(traits.Trait, "default_keys", mock_default_keys):
            dat = {
                "name": "Trait",
                "trait_type": "trait",
                # missing value, now mandatory
                "extra_val": 1000,
            }
            with self.assertRaises(traits.TraitException):
                traits.Trait.validate_input(traits.Trait, dat)

    def test_trait_getset(self):
        """Get-set-del operations on trait"""
        self.assertEqual(self.trait.name, "Test1")
        self.assertEqual(self.trait["name"], "Test1")
        self.assertEqual(self.trait.value, "value")
        self.assertEqual(self.trait["value"], "value")
        self.assertEqual(self.trait.extra_val1, "xvalue1")
        self.assertEqual(self.trait["extra_val2"], "xvalue2")

        self.trait.value = 20
        self.assertEqual(self.trait["value"], 20)
        self.trait["value"] = 20
        self.assertEqual(self.trait.value, 20)
        self.trait.extra_val1 = 100
        self.assertEqual(self.trait.extra_val1, 100)
        # additional properties
        self.trait.foo = "bar"
        self.assertEqual(self.trait.foo, "bar")

        del self.trait.foo
        with self.assertRaises(KeyError):
            self.trait["foo"]
        with self.assertRaises(AttributeError):
            self.trait.foo
        del self.trait.extra_val1
        with self.assertRaises(AttributeError):
            self.trait.extra_val1
        del self.trait.value
        # fall back to default
        self.assertTrue(self.trait.value == traits.Trait.default_keys["value"])

    def test_repr(self):
        self.assertEqual(repr(self.trait), Something)
        self.assertEqual(str(self.trait), Something)


class TestTraitStatic(_TraitHandlerBase):
    """
    Test for static Traits
    """

    def setUp(self):
        super().setUp()
        self.traithandler.add(
            "test1",
            name="Test1",
            trait_type="static",
            base=1,
            mod=2,
            mult=1.0,
            extra_val1="xvalue1",
            extra_val2="xvalue2",
        )
        self.trait = self.traithandler.get("test1")

    def _get_values(self):
        return self.trait.base, self.trait.mod, self.trait.mult, self.trait.value

    def test_init(self):
        self.assertEqual(
            self._get_dbstore("test1"),
            {
                "name": "Test1",
                "trait_type": "static",
                "base": 1,
                "mod": 2,
                "mult": 1.0,
                "extra_val1": "xvalue1",
                "extra_val2": "xvalue2",
            },
        )

    def test_value(self):
        """value is (base + mod) * mult"""
        self.assertEqual(self._get_values(), (1, 2, 1.0, 3))
        self.trait.base += 4
        self.assertEqual(self._get_values(), (5, 2, 1.0, 7))
        self.trait.mod -= 1
        self.assertEqual(self._get_values(), (5, 1, 1.0, 6))
        self.trait.mult += 1.0
        self.assertEqual(self._get_values(), (5, 1, 2.0, 12))
        self.trait.mult = 0.75
        self.assertEqual(self._get_values(), (5, 1, 0.75, 4.5))

    def test_delete(self):
        """Deleting resets to default."""
        self.trait.mult = 2.0
        del self.trait.base
        self.assertEqual(self._get_values(), (0, 2, 2.0, 4))
        del self.trait.mult
        self.assertEqual(self._get_values(), (0, 2, 1.0, 2))
        del self.trait.mod
        self.assertEqual(self._get_values(), (0, 0, 1.0, 0))


class TestTraitCounter(_TraitHandlerBase):
    """
    Test for counter- Traits
    """

    def setUp(self):
        super().setUp()
        self.traithandler.add(
            "test1",
            name="Test1",
            trait_type="counter",
            base=1,
            mod=2,
            mult=1.0,
            min=0,
            max=10,
            extra_val1="xvalue1",
            extra_val2="xvalue2",
            descs={
                0: "range0",
                2: "range1",
                5: "range2",
                7: "range3",
            },
        )
        self.trait = self.traithandler.get("test1")

    def _get_values(self):
        """Get (base, mod, mult, value, min, max)."""
        return (
            self.trait.base,
            self.trait.mod,
            self.trait.mult,
            self.trait.value,
            self.trait.min,
            self.trait.max,
        )

    def test_init(self):
        self.assertEqual(
            self._get_dbstore("test1"),
            {
                "name": "Test1",
                "trait_type": "counter",
                "base": 1,
                "mod": 2,
                "mult": 1.0,
                "min": 0,
                "max": 10,
                "extra_val1": "xvalue1",
                "extra_val2": "xvalue2",
                "descs": {
                    0: "range0",
                    2: "range1",
                    5: "range2",
                    7: "range3",
                },
                "rate": 0,
                "ratetarget": None,
                "last_update": None,
            },
        )

    def test_value(self):
        """value is (current + mod) * mult, where current defaults to base"""
        self.assertEqual(self._get_values(), (1, 2, 1.0, 3, 0, 10))
        self.trait.base += 4
        self.assertEqual(self._get_values(), (5, 2, 1.0, 7, 0, 10))
        self.trait.mod -= 1
        self.assertEqual(self._get_values(), (5, 1, 1.0, 6, 0, 10))
        self.trait.mult += 1.0
        self.assertEqual(self._get_values(), (5, 1, 2.0, 10, 0, 10))

    def test_boundaries__minmax(self):
        """Test range"""
        # should not exceed min/max values
        self.trait.base += 20
        self.assertEqual(self._get_values(), (8, 2, 1.0, 10, 0, 10))
        self.trait.base = 100
        self.assertEqual(self._get_values(), (8, 2, 1.0, 10, 0, 10))
        self.trait.base -= 40
        self.assertEqual(self._get_values(), (-2, 2, 1.0, 0, 0, 10))
        self.trait.base = -100
        self.assertEqual(self._get_values(), (-2, 2, 1.0, 0, 0, 10))

    def test_boundaries__bigmod(self):
        """add a big mod"""
        self.trait.base = 5
        self.trait.mod = 100
        self.assertEqual(self._get_values(), (5, 5, 1.0, 10, 0, 10))
        self.trait.mod = -100
        self.assertEqual(self._get_values(), (5, -5, 1.0, 0, 0, 10))

    def test_boundaries__change_boundaries(self):
        """Change boundaries after base/mod change"""
        self.trait.base = 5
        self.trait.mod = -100
        self.trait.min = -20
        self.assertEqual(self._get_values(), (5, -5, 1.0, 0, -20, 10))
        self.trait.mod -= 100
        self.assertEqual(self._get_values(), (5, -25, 1.0, -20, -20, 10))
        self.trait.mod = 100
        self.trait.max = 20
        self.assertEqual(self._get_values(), (5, 5, 1.0, 10, -20, 20))
        self.trait.mod = 100
        self.assertEqual(self._get_values(), (5, 15, 1.0, 20, -20, 20))

    def test_boundaries__disable(self):
        """Disable and re-enable boundaries"""
        self.trait.base = 5
        self.trait.mod = 100
        self.assertEqual(self._get_values(), (5, 5, 1.0, 10, 0, 10))
        del self.trait.max
        self.assertEqual(self.trait.max, None)
        del self.trait.min
        self.assertEqual(self.trait.min, None)
        self.trait.base = 100
        self.assertEqual(self._get_values(), (100, 5, 1.0, 105, None, None))
        self.trait.base = -200
        self.assertEqual(self._get_values(), (-200, 5, 1.0, -195, None, None))

        # re-activate boundaries
        self.trait.max = 15
        self.trait.min = 10  # his is blocked since base+mod is lower
        self.assertEqual(self._get_values(), (-200, 5, 1.0, -195, -195, 15))

    def test_boundaries__inverse(self):
        """Set inverse boundaries - limited by base"""
        self.trait.mod = 0
        self.assertEqual(self._get_values(), (1, 0, 1.0, 1, 0, 10))
        self.trait.min = 20  # will be set to base
        self.assertEqual(self._get_values(), (1, 0, 1.0, 1, 1, 10))
        self.trait.max = -20
        self.assertEqual(self._get_values(), (1, 0, 1.0, 1, 1, 1))

    def test_current(self):
        """Modifying current value"""
        self.trait.current = 5
        self.assertEqual(self._get_values(), (1, 2, 1.0, 7, 0, 10))
        self.trait.current = 10
        self.assertEqual(self._get_values(), (1, 2, 1.0, 10, 0, 10))
        self.trait.current = 12
        self.assertEqual(self._get_values(), (1, 2, 1.0, 10, 0, 10))
        self.trait.current = -1
        self.assertEqual(self._get_values(), (1, 2, 1.0, 2, 0, 10))
        self.trait.current -= 10
        self.assertEqual(self._get_values(), (1, 2, 1.0, 2, 0, 10))

    def test_delete(self):
        """Deleting resets to default."""
        del self.trait.base
        self.assertEqual(self._get_values(), (0, 2, 1.0, 2, 0, 10))
        del self.trait.mod
        self.assertEqual(self._get_values(), (0, 0, 1.0, 0, 0, 10))
        del self.trait.min
        del self.trait.max
        self.assertEqual(self._get_values(), (0, 0, 1.0, 0, None, None))

    def test_percentage(self):
        """Test percentage calculation"""
        self.trait.base = 8
        self.trait.mod = 2
        self.trait.mult = 1.0
        self.trait.min = 0
        self.trait.max = 10
        self.assertEqual(self.trait.percent(), "100.0%")
        self.trait.current = 3
        self.assertEqual(self.trait.percent(), "50.0%")
        self.trait.current = 1
        self.assertEqual(self.trait.percent(), "30.0%")
        # have to lower this since max cannot be lowered below base+mod
        self.trait.mod = 1
        self.trait.current = 2
        self.trait.max -= 1
        self.assertEqual(self.trait.percent(), "33.3%")
        # open boundary
        del self.trait.min
        self.assertEqual(self.trait.percent(), "100.0%")

    def test_descs(self):
        """Test descriptions"""
        self.trait.min = -5
        self.trait.mod = 0
        self.assertEqual(self._get_values(), (1, 0, 1.0, 1, -5, 10))
        self.trait.current = -2
        self.assertEqual(self.trait.desc(), "range0")
        self.trait.current = 0
        self.assertEqual(self.trait.desc(), "range0")
        self.trait.current = 1
        self.assertEqual(self.trait.desc(), "range1")
        self.trait.current = 3
        self.assertEqual(self.trait.desc(), "range2")
        self.trait.current = 5
        self.assertEqual(self.trait.desc(), "range2")
        self.trait.current = 9
        self.assertEqual(self.trait.desc(), "range3")
        self.trait.current = 100
        self.assertEqual(self.trait.desc(), "range3")


class TestTraitCounterTimed(_TraitHandlerBase):
    """
    Test for trait with timer component
    """

    @patch("evennia.contrib.rpg.traits.traits.time", new=MagicMock(return_value=1000))
    def setUp(self):
        super().setUp()
        self.traithandler.add(
            "test1",
            name="Test1",
            trait_type="counter",
            base=1,
            mod=2,
            mult=1.0,
            min=0,
            max=100,
            extra_val1="xvalue1",
            extra_val2="xvalue2",
            descs={
                0: "range0",
                2: "range1",
                5: "range2",
                7: "range3",
            },
            rate=1,
            ratetarget=None,
        )
        self.trait = self.traithandler.get("test1")

    def _get_timer_data(self):
        return (
            self.trait.value,
            self.trait.current,
            self.trait.rate,
            self.trait._data["last_update"],
            self.trait.ratetarget,
        )

    @patch("evennia.contrib.rpg.traits.traits.time")
    def test_timer_rate(self, mock_time):
        """Test time stepping"""
        mock_time.return_value = 1000
        self.assertEqual(self._get_timer_data(), (3, 1, 1, 1000, None))
        mock_time.return_value = 1001
        self.assertEqual(self._get_timer_data(), (4, 2, 1, 1001, None))
        mock_time.return_value = 1096
        self.assertEqual(self._get_timer_data(), (99, 97, 1, 1096, None))
        # hit maximum boundary
        mock_time.return_value = 1120
        self.assertEqual(self._get_timer_data(), (100, 98, 1, None, None))
        mock_time.return_value = 1200
        self.assertEqual(self._get_timer_data(), (100, 98, 1, None, None))
        # drop current
        self.trait.current = 50
        self.assertEqual(self._get_timer_data(), (52, 50, 1, 1200, None))
        # set a new rate
        self.trait.rate = 2
        mock_time.return_value = 1210
        self.assertEqual(self._get_timer_data(), (72, 70, 2, 1210, None))
        self.trait.rate = -10
        mock_time.return_value = 1214
        self.assertEqual(self._get_timer_data(), (32, 30, -10, 1214, None))
        mock_time.return_value = 1218
        self.assertEqual(self._get_timer_data(), (0, -2, -10, None, None))

    @patch("evennia.contrib.rpg.traits.traits.time")
    def test_timer_ratetarget(self, mock_time):
        """test ratetarget"""
        mock_time.return_value = 1000
        self.trait.ratetarget = 60
        self.assertEqual(self._get_timer_data(), (3, 1, 1, 1000, 60))
        mock_time.return_value = 1056
        self.assertEqual(self._get_timer_data(), (59, 57, 1, 1056, 60))
        mock_time.return_value = 1057
        self.assertEqual(self._get_timer_data(), (60, 58, 1, None, 60))
        mock_time.return_value = 1060
        self.assertEqual(self._get_timer_data(), (60, 58, 1, None, 60))
        self.trait.ratetarget = 70
        mock_time.return_value = 1066
        self.assertEqual(self._get_timer_data(), (66, 64, 1, 1066, 70))
        mock_time.return_value = 1070
        self.assertEqual(self._get_timer_data(), (70, 68, 1, None, 70))


class TestTraitGauge(_TraitHandlerBase):
    def setUp(self):
        super().setUp()
        self.traithandler.add(
            "test1",
            name="Test1",
            trait_type="gauge",
            base=8,  # max = (base + mod) * mult
            mod=2,
            mult=1.0,
            extra_val1="xvalue1",
            extra_val2="xvalue2",
            descs={
                0: "range0",
                2: "range1",
                5: "range2",
                7: "range3",
            },
        )
        self.trait = self.traithandler.get("test1")

    def _get_values(self):
        """Get (base, mod, mult, value, min, max)."""
        return (
            self.trait.base,
            self.trait.mod,
            self.trait.mult,
            self.trait.value,
            self.trait.min,
            self.trait.max,
        )

    def test_init(self):
        self.assertEqual(
            self._get_dbstore("test1"),
            {
                "name": "Test1",
                "trait_type": "gauge",
                "base": 8,
                "mod": 2,
                "mult": 1.0,
                "min": 0,
                "extra_val1": "xvalue1",
                "extra_val2": "xvalue2",
                "descs": {
                    0: "range0",
                    2: "range1",
                    5: "range2",
                    7: "range3",
                },
                "rate": 0,
                "ratetarget": None,
                "last_update": None,
            },
        )

    def test_value(self):
        """value is current, where current defaults to base + mod"""
        # current unset - follows base + mod
        self.assertEqual(self._get_values(), (8, 2, 1.0, 10, 0, 10))
        self.trait.base += 4
        self.assertEqual(self._get_values(), (12, 2, 1.0, 14, 0, 14))
        self.trait.mod -= 1
        self.assertEqual(self._get_values(), (12, 1, 1.0, 13, 0, 13))
        self.trait.mult += 1.0
        self.assertEqual(self._get_values(), (12, 1, 2.0, 26, 0, 26))
        # set current, decouple from base + mod
        self.trait.current = 5
        self.assertEqual(self._get_values(), (12, 1, 2.0, 5, 0, 26))
        self.trait.mod += 1
        self.trait.base -= 4
        self.trait.mult -= 1.0
        self.assertEqual(self._get_values(), (8, 2, 1.0, 5, 0, 10))
        self.trait.min = -100
        self.trait.base = -20
        self.assertEqual(self._get_values(), (-20, 2, 1.0, -18, -100, -18))

    def test_boundaries__minmax(self):
        """Test range"""
        # current unset - tied to base + mod
        self.trait.base += 20
        self.assertEqual(self._get_values(), (28, 2, 1.0, 30, 0, 30))
        # set current - decouple from base + mod
        self.trait.current = 19
        self.assertEqual(self._get_values(), (28, 2, 1.0, 19, 0, 30))
        # test upper bound
        self.trait.current = 100
        self.assertEqual(self._get_values(), (28, 2, 1.0, 30, 0, 30))
        # with multiplier
        self.trait.mult = 2.0
        self.assertEqual(self._get_values(), (28, 2, 2.0, 30, 0, 60))
        self.trait.current = 100
        self.assertEqual(self._get_values(), (28, 2, 2.0, 60, 0, 60))
        # min defaults to 0
        self.trait.mult = 1.0
        self.trait.current = -10
        self.assertEqual(self._get_values(), (28, 2, 1.0, 0, 0, 30))
        self.trait.min = -20
        self.assertEqual(self._get_values(), (28, 2, 1.0, 0, -20, 30))
        self.trait.current = -10
        self.assertEqual(self._get_values(), (28, 2, 1.0, -10, -20, 30))

    def test_boundaries__bigmod(self):
        """add a big mod"""
        self.trait.base = 5
        self.trait.mod = 100
        self.assertEqual(self._get_values(), (5, 100, 1.0, 105, 0, 105))
        # restricted by min
        self.trait.mod = -100
        self.assertEqual(self._get_values(), (5, -5, 1.0, 0, 0, 0))
        self.trait.min = -200
        self.assertEqual(self._get_values(), (5, -5, 1.0, 0, -200, 0))

    def test_boundaries__change_boundaries(self):
        """Change boundaries after current change"""
        self.trait.current = 20
        self.assertEqual(self._get_values(), (8, 2, 1.0, 10, 0, 10))
        self.trait.mod = 102
        self.assertEqual(self._get_values(), (8, 102, 1.0, 10, 0, 110))
        # raising min past current value will force it upwards
        self.trait.min = 20
        self.assertEqual(self._get_values(), (8, 102, 1.0, 20, 20, 110))

    def test_boundaries__disable(self):
        """Disable and re-enable boundary"""
        self.trait.base = 5
        self.trait.min = 1
        self.assertEqual(self._get_values(), (5, 2, 1.0, 7, 1, 7))
        del self.trait.min
        self.assertEqual(self._get_values(), (5, 2, 1.0, 7, 0, 7))
        del self.trait.base
        del self.trait.mod
        self.assertEqual(self._get_values(), (0, 0, 1.0, 0, 0, 0))
        with self.assertRaises(traits.TraitException):
            del self.trait.max

    def test_boundaries__inverse(self):
        """Try to set reversed boundaries"""
        self.trait.mod = 0
        self.trait.base = -10  # limited by min
        self.assertEqual(self._get_values(), (0, 0, 1.0, 0, 0, 0))
        self.trait.min = -10
        self.assertEqual(self._get_values(), (0, 0, 1.0, 0, -10, 0))
        self.trait.base = -10
        self.assertEqual(self._get_values(), (-10, 0, 1.0, -10, -10, -10))
        self.min = 0  # limited by base + mod
        self.assertEqual(self._get_values(), (-10, 0, 1.0, -10, -10, -10))

    def test_current(self):
        """Modifying current value"""
        self.trait.base = 10
        self.trait.current = 5
        self.assertEqual(self._get_values(), (10, 2, 1.0, 5, 0, 12))
        self.trait.current = 10
        self.assertEqual(self._get_values(), (10, 2, 1.0, 10, 0, 12))
        self.trait.current = 12
        self.assertEqual(self._get_values(), (10, 2, 1.0, 12, 0, 12))
        self.trait.current = 0
        self.assertEqual(self._get_values(), (10, 2, 1.0, 0, 0, 12))
        self.trait.current = -1
        self.assertEqual(self._get_values(), (10, 2, 1.0, 0, 0, 12))

    def test_delete(self):
        """Deleting resets to default."""
        del self.trait.mod
        self.assertEqual(self._get_values(), (8, 0, 1.0, 8, 0, 8))
        self.trait.mod = 2
        del self.trait.base
        self.assertEqual(self._get_values(), (0, 2, 1.0, 2, 0, 2))
        del self.trait.min
        self.assertEqual(self._get_values(), (0, 2, 1.0, 2, 0, 2))
        self.trait.min = -10
        self.assertEqual(self._get_values(), (0, 2, 1.0, 2, -10, 2))
        del self.trait.min
        self.assertEqual(self._get_values(), (0, 2, 1.0, 2, 0, 2))

    def test_percentage(self):
        """Test percentage calculation"""
        self.assertEqual(self.trait.percent(), "100.0%")
        self.trait.current = 5
        self.assertEqual(self.trait.percent(), "50.0%")
        self.trait.current = 3
        self.assertEqual(self.trait.percent(), "30.0%")
        self.trait.mod -= 1
        self.assertEqual(self.trait.percent(), "33.3%")

    def test_descs(self):
        """Test descriptions"""
        self.trait.min = -5
        self.assertEqual(self._get_values(), (8, 2, 1.0, 10, -5, 10))
        self.trait.current = -2
        self.assertEqual(self.trait.desc(), "range0")
        self.trait.current = 0
        self.assertEqual(self.trait.desc(), "range0")
        self.trait.current = 1
        self.assertEqual(self.trait.desc(), "range1")
        self.trait.current = 3
        self.assertEqual(self.trait.desc(), "range2")
        self.trait.current = 5
        self.assertEqual(self.trait.desc(), "range2")
        self.trait.current = 9
        self.assertEqual(self.trait.desc(), "range3")
        self.trait.current = 100
        self.assertEqual(self.trait.desc(), "range3")


class TestTraitGaugeTimed(_TraitHandlerBase):
    """
    Test for trait with timer component
    """

    @patch("evennia.contrib.rpg.traits.traits.time", new=MagicMock(return_value=1000))
    def setUp(self):
        super().setUp()
        self.traithandler.add(
            "test1",
            name="Test1",
            trait_type="gauge",
            base=98,
            mod=2,
            min=0,
            extra_val1="xvalue1",
            extra_val2="xvalue2",
            descs={
                0: "range0",
                2: "range1",
                5: "range2",
                7: "range3",
            },
            rate=1,
            ratetarget=None,
        )
        self.trait = self.traithandler.get("test1")

    def _get_timer_data(self):
        return (
            self.trait.value,
            self.trait.current,
            self.trait.rate,
            self.trait._data["last_update"],
            self.trait.ratetarget,
        )

    @patch("evennia.contrib.rpg.traits.traits.time")
    def test_timer_rate(self, mock_time):
        """Test time stepping"""
        mock_time.return_value = 1000
        self.trait.current = 1
        self.assertEqual(self._get_timer_data(), (1, 1, 1, 1000, None))
        mock_time.return_value = 1001
        self.assertEqual(self._get_timer_data(), (2, 2, 1, 1001, None))
        mock_time.return_value = 1096
        self.assertEqual(self._get_timer_data(), (97, 97, 1, 1096, None))
        # hit maximum boundary
        mock_time.return_value = 1120
        self.assertEqual(self._get_timer_data(), (100, 100, 1, None, None))
        mock_time.return_value = 1200
        self.assertEqual(self._get_timer_data(), (100, 100, 1, None, None))
        # drop current
        self.trait.current = 50
        self.assertEqual(self._get_timer_data(), (50, 50, 1, 1200, None))
        # set a new rate
        self.trait.rate = 2
        mock_time.return_value = 1210
        self.assertEqual(self._get_timer_data(), (70, 70, 2, 1210, None))
        self.trait.rate = -10
        mock_time.return_value = 1214
        self.assertEqual(self._get_timer_data(), (30, 30, -10, 1214, None))
        mock_time.return_value = 1218
        self.assertEqual(self._get_timer_data(), (0, 0, -10, None, None))

    @patch("evennia.contrib.rpg.traits.traits.time")
    def test_timer_ratetarget(self, mock_time):
        """test ratetarget"""
        mock_time.return_value = 1000
        self.trait.current = 1
        self.trait.ratetarget = 60
        self.assertEqual(self._get_timer_data(), (1, 1, 1, 1000, 60))
        mock_time.return_value = 1056
        self.assertEqual(self._get_timer_data(), (57, 57, 1, 1056, 60))
        mock_time.return_value = 1059
        self.assertEqual(self._get_timer_data(), (60, 60, 1, None, 60))
        mock_time.return_value = 1060
        self.assertEqual(self._get_timer_data(), (60, 60, 1, None, 60))
        self.trait.ratetarget = 70
        mock_time.return_value = 1066
        self.assertEqual(self._get_timer_data(), (66, 66, 1, 1066, 70))
        mock_time.return_value = 1070
        self.assertEqual(self._get_timer_data(), (70, 70, 1, None, 70))


class TestNumericTraitOperators(BaseEvenniaTestCase):
    """Test case for numeric magic method implementations."""

    def setUp(self):
        # direct instantiation for testing only; use TraitHandler in production
        self.st = traits.Trait(
            {
                "name": "Strength",
                "trait_type": "trait",
                "value": 8,
            }
        )
        self.at = traits.Trait(
            {
                "name": "Attack",
                "trait_type": "trait",
                "value": 4,
            }
        )

    def tearDown(self):
        self.st, self.at = None, None

    def test_pos_shortcut(self):
        """overridden unary + operator returns `value` property"""
        self.assertIn(type(+self.st), (float, int))
        self.assertEqual(+self.st, self.st.value)
        self.assertEqual(+self.st, 8)

    def test_add_traits(self):
        """test addition of `Trait` objects"""
        # two Trait objects
        self.assertEqual(self.st + self.at, 12)
        # Trait and numeric
        self.assertEqual(self.st + 1, 9)
        self.assertEqual(1 + self.st, 9)

    def test_sub_traits(self):
        """test subtraction of `Trait` objects"""
        # two Trait objects
        self.assertEqual(self.st - self.at, 4)
        # Trait and numeric
        self.assertEqual(self.st - 1, 7)
        self.assertEqual(10 - self.st, 2)

    def test_mul_traits(self):
        """test multiplication of `Trait` objects"""
        # between two Traits
        self.assertEqual(self.st * self.at, 32)
        # between Trait and numeric
        self.assertEqual(self.at * 4, 16)
        self.assertEqual(4 * self.at, 16)

    def test_floordiv(self):
        """test floor division of `Trait` objects"""
        # between two Traits
        self.assertEqual(self.st // self.at, 2)
        # between Trait and numeric
        self.assertEqual(self.st // 2, 4)
        self.assertEqual(18 // self.st, 2)

    def test_comparisons_traits(self):
        """test equality comparison between `Trait` objects"""
        self.assertNotEqual(self.st, self.at)
        self.assertLess(self.at, self.st)
        self.assertLessEqual(self.at, self.st)
        self.assertGreater(self.st, self.at)
        self.assertGreaterEqual(self.st, self.at)

    def test_comparisons_numeric(self):
        """equality comparisons between `Trait` and numeric"""
        self.assertEqual(self.st, 8)
        self.assertEqual(8, self.st)
        self.assertNotEqual(self.st, 0)
        self.assertNotEqual(0, self.st)
        self.assertLess(self.st, 10)
        self.assertLess(0, self.st)
        self.assertLessEqual(self.st, 8)
        self.assertLessEqual(8, self.st)
        self.assertLessEqual(self.st, 10)
        self.assertLessEqual(0, self.st)
        self.assertGreater(self.st, 0)
        self.assertGreater(10, self.st)
        self.assertGreaterEqual(self.st, 8)
        self.assertGreaterEqual(8, self.st)
        self.assertGreaterEqual(self.st, 0)
        self.assertGreaterEqual(10, self.st)


class DummyCharacter(_MockObj):
    strength = traits.TraitProperty("Strength", trait_type="static", base=10, mod=2)
    hunting = traits.TraitProperty("Hunting skill", trait_type="counter", base=10, mod=1, max=100)
    health = traits.TraitProperty("Health value", trait_type="gauge", base=100)


class TestTraitFields(BaseEvenniaTestCase):
    """
    Test the TraitField class.

    """

    @patch("evennia.contrib.rpg.traits.traits._TRAIT_CLASS_PATHS", new=_TEST_TRAIT_CLASS_PATHS)
    def test_traitfields(self):
        obj = DummyCharacter()
        obj2 = DummyCharacter()

        self.assertEqual(12, obj.strength.value)
        self.assertEqual(11, obj.hunting.value)
        self.assertEqual(100, obj.health.value)

        obj.strength.base += 5
        self.assertEqual(17, obj.strength.value)

        obj.strength.berserk = True
        self.assertEqual(obj.strength.berserk, True)

        self.assertEqual(100, obj.traits.health)
        self.assertEqual(None, obj.traits.hp)

        # the traithandler still works
        obj.traits.health.current -= 1
        self.assertEqual(99, obj.health.value)

        # making sure Descriptors are separate
        self.assertEqual(12, obj2.strength.value)
        self.assertEqual(17, obj.strength.value)

        obj2.strength.base += 1
        obj.strength.base += 3

        self.assertEqual(13, obj2.strength.value)
        self.assertEqual(20, obj.strength.value)


class TraitContribTestingChar(DefaultCharacter):
    HP = traits.TraitProperty("health", trait_type="trait", value=5)


class TraitPropertyTestCase(EvenniaTest):
    """
    Test atomic updating.

    """

    character_typeclass = TraitContribTestingChar

    def test_round1(self):
        self.char1.HP.value = 1

    def test_round2(self):
        self.char1.HP.value = 2
