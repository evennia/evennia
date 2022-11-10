"""
Tests for the buff system contrib
"""
from unittest.mock import Mock, call, patch

from evennia import DefaultObject, create_object
from evennia.contrib.rpg.buffs import buff
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from evennia.utils.utils import lazy_property

from .buff import BaseBuff, BuffableProperty, BuffHandler, Mod
from .samplebuffs import StatBuff


class _EmptyBuff(BaseBuff):
    key = "empty"
    pass


class _TestDivBuff(BaseBuff):
    key = "tdb"
    name = "tdb"
    flavor = "divverbuff"
    mods = [Mod("stat1", "div", 1)]


class _TestModBuff(BaseBuff):
    key = "tmb"
    name = "tmb"
    flavor = "modderbuff"
    maxstacks = 5
    mods = [Mod("stat1", "add", 10, 5), Mod("stat2", "mult", 0.5)]


class _TestModBuff2(BaseBuff):
    key = "tmb2"
    name = "tmb2"
    flavor = "modderbuff2"
    maxstacks = 1
    mods = [Mod("stat1", "mult", 1.0), Mod("stat1", "add", 10)]


class _TestTrigBuff(BaseBuff):
    key = "ttb"
    name = "ttb"
    flavor = "triggerbuff"
    triggers = ["test1", "test2"]

    def at_trigger(self, trigger: str, *args, **kwargs):
        if trigger == "test1":
            self.owner.db.triggertest1 = True
        if trigger == "test2":
            self.owner.db.triggertest2 = True


class _TestConBuff(BaseBuff):
    key = "tcb"
    name = "tcb"
    flavor = "condbuff"
    triggers = ["condtest"]

    def conditional(self, *args, **kwargs):
        return self.owner.db.cond1

    def at_trigger(self, trigger: str, attacker=None, defender=None, damage=0, *args, **kwargs):
        defender.db.att, defender.db.dmg = attacker, damage


class _TestComplexBuff(BaseBuff):
    key = "tcomb"
    name = "complex"
    flavor = "combuff"
    triggers = ["comtest", "complextest"]

    mods = [
        Mod("com1", "add", 0, 10),
        Mod("com1", "add", 15),
        Mod("com1", "mult", 2.0),
        Mod("com2", "add", 100),
    ]

    def conditional(self, cond=False, *args, **kwargs):
        return not cond

    def at_trigger(self, trigger: str, *args, **kwargs):
        if trigger == "comtest":
            self.owner.db.comtext = {"cond": True}
        else:
            self.owner.db.comtext = {}


class _TestTimeBuff(BaseBuff):
    key = "ttib"
    name = "ttib"
    flavor = "timerbuff"
    maxstacks = 1
    tickrate = 1
    duration = 5
    mods = [Mod("timetest", "add", 665)]

    def at_tick(self, initial=True, *args, **kwargs):
        self.owner.db.ticktest = True


class BuffableObject(DefaultObject):
    stat1 = BuffableProperty(10)

    @lazy_property
    def buffs(self) -> BuffHandler:
        return BuffHandler(self)

    def at_init(self):
        self.stat1, self.buffs
        return super().at_init()


class TestBuffsAndHandler(EvenniaTest):
    "This tests a number of things about buffs."

    def setUp(self):
        super().setUp()
        self.testobj = create.create_object(BuffableObject, key="testobj")

    def tearDown(self):
        """done after every test_* method below"""
        self.testobj.buffs.clear()
        del self.testobj
        super().tearDown()

    @patch("evennia.contrib.rpg.buffs.buff.utils.delay", new=Mock())
    def test_addremove(self):
        """tests adding and removing buffs"""
        # setup
        handler: BuffHandler = self.testobj.buffs
        # add
        handler.add(_TestModBuff, to_cache={"cachetest": True})
        handler.add(_TestTrigBuff)
        self.assertEqual(self.testobj.db.buffs["tmb"]["ref"], _TestModBuff)
        self.assertTrue(self.testobj.db.buffs["tmb"].get("cachetest"))
        self.assertFalse(self.testobj.db.buffs["ttb"].get("cachetest"))
        # has
        self.assertTrue(handler.has(_TestModBuff))
        self.assertTrue(handler.has("tmb"))
        self.assertFalse(handler.has(_EmptyBuff))
        # remove
        handler.remove("tmb")
        self.assertFalse(self.testobj.db.buffs.get("tmb"))
        # remove stacks
        handler.add(_TestModBuff, stacks=3)
        handler.remove("tmb", stacks=3)
        self.assertFalse(self.testobj.db.buffs.get("tmb"))
        # remove by type
        handler.add(_TestModBuff)
        handler.remove_by_type(_TestModBuff)
        self.assertFalse(self.testobj.db.buffs.get("tmb"))
        # remove by buff instance
        handler.add(_TestModBuff)
        handler.all["tmb"].remove()
        self.assertFalse(self.testobj.db.buffs.get("tmb"))
        # remove by source
        handler.add(_TestModBuff)
        handler.remove_by_source(None)
        self.assertFalse(self.testobj.db.buffs.get("tmb"))
        # remove by cachevalue
        handler.add(_TestModBuff)
        handler.remove_by_cachevalue("failure", True)
        self.assertTrue(self.testobj.db.buffs.get("tmb"))
        # remove all
        handler.add(_TestModBuff)
        handler.clear()
        self.assertFalse(self.testobj.buffs.all)

    @patch("evennia.contrib.rpg.buffs.buff.utils.delay", new=Mock())
    def test_getters(self):
        """tests all built-in getters"""
        # setup
        handler: BuffHandler = self.testobj.buffs
        handler.add(_TestModBuff, source=self.obj2)
        handler.add(_TestTrigBuff, to_cache={"ttbcache": True})
        # normal getter
        self.assertTrue(isinstance(handler.get("tmb"), _TestModBuff))
        # stat getters
        self.assertTrue(isinstance(handler.get_by_stat("stat1")["tmb"], _TestModBuff))
        self.assertFalse(handler.get_by_stat("nullstat"))
        # trigger getters
        self.assertTrue("ttb" in handler.get_by_trigger("test1").keys())
        self.assertFalse("ttb" in handler.get_by_trigger("nulltrig").keys())
        # type getters
        self.assertTrue("tmb" in handler.get_by_type(_TestModBuff))
        self.assertFalse("tmb" in handler.get_by_type(_EmptyBuff))
        # source getter
        self.assertTrue("tmb" in handler.get_by_source(self.obj2))
        self.assertFalse("ttb" in handler.get_by_source(self.obj2))
        # cachevalue getter
        self.assertFalse("tmb" in handler.get_by_cachevalue("ttbcache"))
        self.assertTrue("ttb" in handler.get_by_cachevalue("ttbcache"))
        self.assertTrue("ttb" in handler.get_by_cachevalue("ttbcache", True))

    @patch("evennia.contrib.rpg.buffs.buff.utils.delay", new=Mock())
    def test_details(self):
        """tests that buff details like name and flavor are correct; also test modifier viewing"""
        handler: BuffHandler = self.testobj.buffs
        handler.add(_TestModBuff)
        handler.add(_TestTrigBuff)
        self.assertEqual(handler.get("tmb").flavor, "modderbuff")
        self.assertEqual(handler.get("ttb").name, "ttb")
        mods = handler.view_modifiers("stat1")
        _testmods = {
            "add": {"total": 15, "strongest": 15},
            "mult": {"total": 0, "strongest": 0},
            "div": {"total": 0, "strongest": 0},
        }
        self.assertDictEqual(mods, _testmods)

    @patch("evennia.contrib.rpg.buffs.buff.utils.delay", new=Mock())
    def test_modify(self):
        """tests to ensure that values are modified correctly, and stack across mods"""
        # setup
        handler: BuffHandler = self.testobj.buffs
        _stat1, _stat2 = 0, 10
        handler.add(_TestModBuff)
        # stat1 and 2 basic mods
        self.assertEqual(handler.check(_stat1, "stat1"), 15)
        self.assertEqual(handler.check(_stat2, "stat2"), 15)
        # checks can take any base value
        self.assertEqual(handler.check(_stat1, "stat2"), 0)
        self.assertEqual(handler.check(_stat2, "stat1"), 25)
        # change to base stat reflected in check
        _stat1 += 5
        self.assertEqual(handler.check(_stat1, "stat1"), 20)
        _stat2 += 10
        self.assertEqual(handler.check(_stat2, "stat2"), 30)
        # test stacking; single stack, multiple stack, max stacks
        handler.add(_TestModBuff)
        self.assertEqual(handler.check(_stat1, "stat1"), 25)
        handler.add(_TestModBuff, stacks=3)
        self.assertEqual(handler.check(_stat1, "stat1"), 40)
        handler.add(_TestModBuff, stacks=5)
        self.assertEqual(handler.check(_stat1, "stat1"), 40)
        # stat2 mod doesn't stack
        self.assertEqual(handler.check(_stat2, "stat2"), 30)
        # layers with second mod
        handler.add(_TestModBuff2)
        self.assertEqual(handler.check(_stat1, "stat1"), 100)
        self.assertEqual(handler.check(_stat2, "stat2"), 30)
        # apply only the strongest value
        self.assertEqual(handler.check(_stat1, "stat1", strongest=True), 80)
        # removing mod properly reduces value, doesn't affect other mods
        handler.remove_by_type(_TestModBuff)
        self.assertEqual(handler.check(_stat1, "stat1"), 30)
        self.assertEqual(handler.check(_stat2, "stat2"), 20)
        # divider mod test
        handler.add(_TestDivBuff)
        self.assertEqual(handler.check(_stat1, "stat1"), 15)

    @patch("evennia.contrib.rpg.buffs.buff.utils.delay", new=Mock())
    def test_trigger(self):
        """tests to ensure triggers correctly fire"""
        # setup
        handler: BuffHandler = self.testobj.buffs
        handler.add(_TestTrigBuff)
        # trigger buffs
        handler.trigger("nulltest")
        self.assertFalse(self.testobj.db.triggertest1)
        self.assertFalse(self.testobj.db.triggertest2)
        handler.trigger("test1")
        self.assertTrue(self.testobj.db.triggertest1)
        self.assertFalse(self.testobj.db.triggertest2)
        handler.trigger("test2")
        self.assertTrue(self.testobj.db.triggertest1)
        self.assertTrue(self.testobj.db.triggertest2)

    @patch("evennia.contrib.rpg.buffs.buff.utils.delay", new=Mock())
    def test_context_conditional(self):
        """tests to ensure context is passed to buffs, and also tests conditionals"""
        # setup
        handler: BuffHandler = self.testobj.buffs
        handler.add(_TestConBuff)
        self.testobj.db.cond1, self.testobj.db.att, self.testobj.db.dmg = False, None, 0
        # context to pass, containing basic event data and a little extra to be ignored
        _testcontext = {
            "attacker": self.obj2,
            "defender": self.testobj,
            "damage": 5,
            "overflow": 10,
        }
        # test negative conditional
        self.assertEqual(
            handler.get_by_type(_TestConBuff)["tcb"].conditional(**_testcontext), False
        )
        handler.trigger("condtest", _testcontext)
        self.assertEqual(self.testobj.db.att, None)
        self.assertEqual(self.testobj.db.dmg, 0)
        # test positive conditional + context passing
        self.testobj.db.cond1 = True
        self.assertEqual(handler.get_by_type(_TestConBuff)["tcb"].conditional(**_testcontext), True)
        handler.trigger("condtest", _testcontext)
        self.assertEqual(self.testobj.db.att, self.obj2)
        self.assertEqual(self.testobj.db.dmg, 5)

    @patch("evennia.contrib.rpg.buffs.buff.utils.delay", new=Mock())
    def test_complex(self):
        """tests a complex mod (conditionals, multiple triggers/mods)"""
        # setup
        handler: BuffHandler = self.testobj.buffs
        self.testobj.db.comone, self.testobj.db.comtwo, self.testobj.db.comtext = 10, 0, {}
        handler.add(_TestComplexBuff)
        # stat checks work correctly and separately
        self.assertEqual(self.testobj.db.comtext, {})
        self.assertEqual(handler.check(self.testobj.db.comone, "com1"), 105)
        self.assertEqual(handler.check(self.testobj.db.comtwo, "com2"), 100)
        # stat checks don't happen if the conditional is true
        handler.trigger("comtest", self.testobj.db.comtext)
        self.assertEqual(self.testobj.db.comtext, {"cond": True})
        self.assertEqual(
            handler.get_by_type(_TestComplexBuff)["tcomb"].conditional(**self.testobj.db.comtext),
            False,
        )
        self.assertEqual(
            handler.check(self.testobj.db.comone, "com1", context=self.testobj.db.comtext), 10
        )
        self.assertEqual(
            handler.check(self.testobj.db.comtwo, "com2", context=self.testobj.db.comtext), 0
        )
        handler.trigger("complextest", self.testobj.db.comtext)
        self.assertEqual(
            handler.check(self.testobj.db.comone, "com1", context=self.testobj.db.comtext), 10
        )
        self.assertEqual(
            handler.check(self.testobj.db.comtwo, "com2", context=self.testobj.db.comtext), 0
        )
        # separate trigger follows different codepath
        self.testobj.db.comtext = {"cond": False}
        handler.trigger("complextest", self.testobj.db.comtext)
        self.assertEqual(self.testobj.db.comtext, {})
        self.assertEqual(
            handler.check(self.testobj.db.comone, "com1", context=self.testobj.db.comtext), 105
        )
        self.assertEqual(
            handler.check(self.testobj.db.comtwo, "com2", context=self.testobj.db.comtext), 100
        )

    @patch("evennia.contrib.rpg.buffs.buff.utils.delay")
    def test_timing(self, mock_delay: Mock):
        """tests timing-related features, such as ticking and duration"""
        # setup
        handler: BuffHandler = self.testobj.buffs
        mock_delay.side_effect = [None, handler.cleanup]
        handler.add(_TestTimeBuff)
        calls = [
            call(
                1,
                buff.tick_buff,
                handler=handler,
                buffkey="ttib",
                context={},
                initial=False,
                persistent=True,
            ),
            call(5, handler.cleanup, persistent=True),
        ]
        mock_delay.assert_has_calls(calls)
        self.testobj.db.timetest, self.testobj.db.ticktest = 1, False
        # test duration and ticking
        _instance = handler.get("ttib")
        self.assertTrue(_instance.ticking)
        self.assertEqual(_instance.duration, 5)
        _instance.at_tick()
        self.assertTrue(self.testobj.db.ticktest)
        # test duration modification and cleanup
        _instance.duration = 0
        self.assertEqual(handler.get("ttib").duration, 0)
        handler.cleanup()
        self.assertFalse(handler.get("ttib"), None)

    @patch("evennia.contrib.rpg.buffs.buff.utils.delay", new=Mock())
    def test_cacheattrlink(self):
        """tests the link between the instance attribute and the cache attribute"""
        # setup
        handler: BuffHandler = self.testobj.buffs
        handler.add(_EmptyBuff)
        self.assertEqual(handler.buffcache["empty"]["duration"], -1)
        empty: _EmptyBuff = handler.get("empty")
        empty.duration = 30
        self.assertEqual(handler.buffcache["empty"]["duration"], 30)

    @patch("evennia.contrib.rpg.buffs.buff.utils.delay", new=Mock())
    def test_buffableproperty(self):
        """tests buffable properties"""
        # setup
        self.testobj.buffs.add(_TestModBuff)
        self.assertEqual(self.testobj.stat1, 25)
        self.testobj.buffs.remove("tmb")
        self.assertEqual(self.testobj.stat1, 10)

    @patch("evennia.contrib.rpg.buffs.buff.utils.delay", new=Mock())
    def test_stresstest(self):
        """tests large amounts of buffs, and related removal methods"""
        # setup
        for x in range(1, 20):
            self.testobj.buffs.add(_TestModBuff, key="test" + str(x))
            self.testobj.buffs.add(_TestTrigBuff, key="trig" + str(x))
        self.assertEqual(self.testobj.stat1, 295)
        self.testobj.buffs.trigger("test1")
        self.testobj.buffs.remove_by_type(_TestModBuff)
        self.assertEqual(self.testobj.stat1, 10)
        self.testobj.buffs.clear()
        self.assertFalse(self.testobj.buffs.all)

    @patch("evennia.contrib.rpg.buffs.buff.utils.delay", new=Mock())
    def test_modgen(self):
        """test generating mods on the fly"""
        # setup
        handler: BuffHandler = self.testobj.buffs
        self.testobj.db.gentest = 5
        self.assertEqual(self.testobj.db.gentest, 5)
        tc = {"modgen": ["gentest", "add", 5, 0]}
        handler.add(StatBuff, key="gentest", to_cache=tc)
        self.assertEqual(handler.check(self.testobj.db.gentest, "gentest"), 10)
        tc = {"modgen": ["gentest", "add", 10, 0]}
        handler.add(StatBuff, key="gentest", to_cache=tc)
        self.assertEqual(handler.check(self.testobj.db.gentest, "gentest"), 15)
        self.assertEqual(
            handler.get("gentest").flavor, "This buff affects the following stats: gentest"
        )
