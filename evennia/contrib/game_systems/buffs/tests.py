# in a module tests.py somewhere i your game dir
from unittest.mock import Mock, patch
from evennia import DefaultObject, create_object
from evennia.utils import create
from evennia.utils.utils import lazy_property
# the function we want to test
from .buff import BaseBuff, Mod, BuffHandler, BuffableProperty
from evennia.utils.test_resources import EvenniaTest

class _EmptyBuff(BaseBuff):
    pass

class _TestModBuff(BaseBuff):
    key = 'tmb'
    name = 'tmb'
    flavor = 'modderbuff'
    maxstacks = 5
    mods = [
        Mod('stat1', 'add', 10, 5),
        Mod('stat2', 'mult', 0.5)
    ]

class _TestModBuff2(BaseBuff):
    key = 'tmb2'
    name = 'tmb2'
    flavor = 'modderbuff2'
    maxstacks = 1
    mods = [
        Mod('stat1', 'mult', 1.0),
        Mod('stat1', 'add', 10)
    ]

class _TestTrigBuff(BaseBuff):
    key = 'ttb'
    name = 'ttb'
    flavor = 'triggerbuff'
    triggers = ['test1', 'test2']

    def on_trigger(self, trigger: str, *args, **kwargs):
        if trigger == 'test1': self.owner.db.triggertest1 = True
        if trigger == 'test2': self.owner.db.triggertest2 = True

class _TestConBuff(BaseBuff):
    key = 'tcb'
    name = 'tcb'
    flavor = 'condbuff'
    triggers = ['condtest']

    def conditional(self, *args, **kwargs):
        return self.owner.db.cond1

    def on_trigger(self, trigger: str, attacker=None, defender=None, damage=0, *args, **kwargs):
        defender.db.att, defender.db.dmg = attacker, damage

class _TestComplexBuff(BaseBuff):
    key = 'tcomb'
    name = 'complex'
    flavor = 'combuff'
    triggers = ['comtest', 'complextest']

    mods = [
        Mod('com1', 'add', 0, 10),
        Mod('com1', 'add', 15),
        Mod('com1', 'mult', 2.0),
        Mod('com2', 'add', 100)
    ]

    def conditional(self, cond=False, *args, **kwargs):
        return not cond

    def on_trigger(self, trigger: str, *args, **kwargs):
        if trigger == 'comtest': self.owner.db.comtext = {'cond': True}
        else: self.owner.db.comtext = {}

class _TestTimeBuff(BaseBuff):
    key = 'ttib'
    name = 'ttib'
    flavor = 'timerbuff'
    maxstacks = 1
    tickrate = 1
    duration = 5
    mods = [Mod('timetest', 'add', 665)]

    def on_tick(self, initial=True, *args, **kwargs):
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
        self.obj1.handler = BuffHandler(self.obj1, 'buffs')
        
    def tearDown(self):
        """done after every test_* method below """
        super().tearDown()

    def test_addremove(self):
        '''tests adding and removing buffs'''
        # setup
        handler: BuffHandler = self.obj1.handler
        # add
        handler.add(_TestModBuff)
        self.assertEqual( self.obj1.db.buffs['tmb']['ref'], _TestModBuff)
        # remove
        handler.remove('tmb')
        self.assertEqual( self.obj1.db.buffs.get('tmb'), None)
        # remove by type
        handler.add(_TestModBuff)
        handler.remove_by_type(_TestModBuff)
        self.assertEqual( self.obj1.db.buffs.get('tmb'), None)
        # remove by buff instance
        handler.add(_TestModBuff)
        handler.all['tmb'].remove()
        self.assertEqual( self.obj1.db.buffs.get('tmb'), None)

    def test_getters(self):
        '''tests all built-in getters'''
        # setup
        handler: BuffHandler = self.obj1.handler
        handler.add(_TestModBuff)
        handler.add(_TestTrigBuff)
        # normal getters
        self.assertEqual(isinstance(handler.tmb, _TestModBuff), True)
        self.assertEqual(isinstance(handler.get('tmb'),_TestModBuff), True)
        # stat getters
        self.assertEqual(isinstance(handler.get_by_stat('stat1')['tmb'], _TestModBuff), True)
        self.assertEqual(handler.get_by_stat('nullstat'), {})
        # trigger getters
        self.assertEqual('ttb' in handler.get_by_trigger('test1').keys(), True)
        self.assertEqual('ttb' in handler.get_by_trigger('nulltrig').keys(), False)
        # type getters
        self.assertEqual('tmb' in handler.get_by_type(_TestModBuff), True)
        self.assertEqual('tmb' in handler.get_by_type(_EmptyBuff), False)
    
    def test_details(self):
        '''tests that buff details like name and flavor are correct'''
        handler: BuffHandler = self.obj1.handler
        handler.add(_TestModBuff)
        handler.add(_TestTrigBuff)
        self.assertEqual(handler.tmb.flavor, 'modderbuff')
        self.assertEqual(handler.ttb.name, 'ttb')
    
    def test_modify(self):
        '''tests to ensure that values are modified correctly, and stack across mods'''
        # setup
        handler: BuffHandler = self.obj1.handler
        _stat1, _stat2 = 0, 10
        handler.add(_TestModBuff)
        # stat1 and 2 basic mods
        self.assertEqual(handler.check(_stat1, 'stat1'), 15)
        self.assertEqual(handler.check(_stat2, 'stat2'), 15)
        # checks can take any base value
        self.assertEqual(handler.check(_stat1, 'stat2'), 0)
        self.assertEqual(handler.check(_stat2, 'stat1'), 25)
        # change to base stat reflected in check
        _stat1 += 5
        self.assertEqual(handler.check(_stat1, 'stat1'), 20)
        _stat2 += 10
        self.assertEqual(handler.check(_stat2, 'stat2'), 30)
        # test stacking; single stack, multiple stack, max stacks
        handler.add(_TestModBuff)
        self.assertEqual(handler.check(_stat1, 'stat1'), 25)
        handler.add(_TestModBuff, stacks=3)
        self.assertEqual(handler.check(_stat1, 'stat1'), 40)
        handler.add(_TestModBuff, stacks=5)
        self.assertEqual(handler.check(_stat1, 'stat1'), 40)
        # stat2 mod doesn't stack
        self.assertEqual(handler.check(_stat2, 'stat2'), 30)
        # layers with second mod
        handler.add(_TestModBuff2)
        self.assertEqual(handler.check(_stat1, 'stat1'), 100)
        self.assertEqual(handler.check(_stat2, 'stat2'), 30)
        handler.remove_by_type(_TestModBuff)
        self.assertEqual(handler.check(_stat1, 'stat1'), 30)
        self.assertEqual(handler.check(_stat2, 'stat2'), 20)
    
    def test_trigger(self):
        '''tests to ensure triggers correctly fire'''
        # setup
        handler: BuffHandler = self.obj1.handler
        handler.add(_TestTrigBuff)
        # trigger buffs
        handler.trigger('nulltest')
        self.assertEqual(self.obj1.db.triggertest1, None)
        self.assertEqual(self.obj1.db.triggertest2, None)
        handler.trigger('test1')
        self.assertEqual(self.obj1.db.triggertest1, True)
        self.assertEqual(self.obj1.db.triggertest2, None)
        handler.trigger('test2')
        self.assertEqual(self.obj1.db.triggertest1, True)
        self.assertEqual(self.obj1.db.triggertest2, True)

    def test_context_conditional(self):
        '''tests to ensure context is passed to buffs, and also tests conditionals'''
        # setup
        handler: BuffHandler = self.obj1.handler
        handler.add(_TestConBuff)
        self.obj1.db.cond1, self.obj1.db.att, self.obj1.db.dmg = False, None, 0
        # context to pass, containing basic event data and a little extra to be ignored
        _testcontext = {'attacker':self.obj2, 'defender':self.obj1, 'damage':5, 'overflow':10} 
        # test negative conditional
        self.assertEqual(handler.get_by_type(_TestConBuff)['tcb'].conditional(**_testcontext), False)
        handler.trigger('condtest', _testcontext)
        self.assertEqual(self.obj1.db.att, None)
        self.assertEqual(self.obj1.db.dmg, 0)
        # test positive conditional + context passing
        self.obj1.db.cond1 = True
        self.assertEqual(handler.get_by_type(_TestConBuff)['tcb'].conditional(**_testcontext), True)
        handler.trigger('condtest', _testcontext)
        self.assertEqual(self.obj1.db.att, self.obj2)
        self.assertEqual(self.obj1.db.dmg, 5)
    
    def test_complex(self):
        '''tests a complex mod (conditionals, multiple triggers/mods)'''
        # setup
        handler: BuffHandler = self.obj1.handler
        self.obj1.db.comone, self.obj1.db.comtwo, self.obj1.db.comtext = 10, 0, {}
        handler.add(_TestComplexBuff)
        # stat checks work correctly and separately
        self.assertEqual(self.obj1.db.comtext, {})
        self.assertEqual(handler.check(self.obj1.db.comone, 'com1'), 105)
        self.assertEqual(handler.check(self.obj1.db.comtwo, 'com2'), 100)
        # stat checks don't happen if the conditional is true
        handler.trigger('comtest', self.obj1.db.comtext)
        self.assertEqual(self.obj1.db.comtext, {'cond': True})
        self.assertEqual(handler.get_by_type(_TestComplexBuff)['tcomb'].conditional(**self.obj1.db.comtext), False)
        self.assertEqual(handler.check(self.obj1.db.comone, 'com1', context=self.obj1.db.comtext), 10)
        self.assertEqual(handler.check(self.obj1.db.comtwo, 'com2', context=self.obj1.db.comtext), 0)
        handler.trigger('complextest', self.obj1.db.comtext)
        self.assertEqual(handler.check(self.obj1.db.comone, 'com1', context=self.obj1.db.comtext), 10)
        self.assertEqual(handler.check(self.obj1.db.comtwo, 'com2', context=self.obj1.db.comtext), 0)
        # separate trigger follows different codepath
        self.obj1.db.comtext = {'cond': False}
        handler.trigger('complextest', self.obj1.db.comtext)
        self.assertEqual(self.obj1.db.comtext, {})
        self.assertEqual(handler.check(self.obj1.db.comone, 'com1', context=self.obj1.db.comtext), 105)
        self.assertEqual(handler.check(self.obj1.db.comtwo, 'com2', context=self.obj1.db.comtext), 100)

    def test_timing(self):
        '''tests timing-related features, such as ticking and duration'''
        # setup
        handler: BuffHandler = self.obj1.handler
        handler.add(_TestTimeBuff)
        self.obj1.db.timetest, self.obj1.db.ticktest = 1, False
        # test duration and ticking
        self.assertTrue(handler.ttib.ticking)
        self.assertEqual(handler.get('ttib').duration, 5)
        handler.get('ttib').on_tick()
        self.assertTrue(self.obj1.db.ticktest)
        # test duration modification and cleanup
        handler.modify_duration('ttib', 0, set=True)
        self.assertEqual(handler.get('ttib').duration, 0)
        handler.cleanup()
        self.assertFalse(handler.get('ttib'), None)
    
    def test_buffableproperty(self):
        '''tests buffable properties'''
        # setup
        self.propobj = create.create_object(BuffableObject, key='testobj')
        self.propobj.buffs.add(_TestModBuff)
        self.assertEqual(self.propobj.stat1, 25)
        self.propobj.buffs.remove('tmb')
        self.assertEqual(self.propobj.stat1, 10)
