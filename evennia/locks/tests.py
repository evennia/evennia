# -*- coding: utf-8 -*-

"""
This is part of Evennia's unittest framework, for testing
the stability and integrity of the codebase during updates.

This module tests the lock functionality of Evennia.

"""
from evennia.utils.test_resources import EvenniaTest

try:
    # this is a special optimized Django version, only available in current Django devel
    from django.utils.unittest import TestCase, override_settings
except ImportError:
    from django.test import TestCase, override_settings

from evennia import settings_default
from evennia.locks import lockfuncs

# ------------------------------------------------------------
# Lock testing
# ------------------------------------------------------------


class TestLockCheck(EvenniaTest):
    def testrun(self):
        dbref = self.obj2.dbref
        self.obj1.locks.add("owner:dbref(%s);edit:dbref(%s) or perm(Admin);examine:perm(Builder) "
                            "and id(%s);delete:perm(Admin);get:all()" % (dbref, dbref, dbref))
        self.obj2.permissions.add('Admin')
        self.assertEquals(True, self.obj1.locks.check(self.obj2, 'owner'))
        self.assertEquals(True, self.obj1.locks.check(self.obj2, 'edit'))
        self.assertEquals(True, self.obj1.locks.check(self.obj2, 'examine'))
        self.assertEquals(True, self.obj1.locks.check(self.obj2, 'delete'))
        self.assertEquals(True, self.obj1.locks.check(self.obj2, 'get'))
        self.obj1.locks.add("get:false()")
        self.assertEquals(False, self.obj1.locks.check(self.obj2, 'get'))
        self.assertEquals(True, self.obj1.locks.check(self.obj2, 'not_exist', default=True))

class TestLockfuncs(EvenniaTest):
    def setUp(self):
        super(TestLockfuncs, self).setUp()
        self.account2.permissions.add('Admin')
        self.char2.permissions.add('Builder')

    def test_booleans(self):
        self.assertEquals(True, lockfuncs.true(self.account2, self.obj1))
        self.assertEquals(True, lockfuncs.all(self.account2, self.obj1))
        self.assertEquals(False, lockfuncs.false(self.account2, self.obj1))
        self.assertEquals(False, lockfuncs.none(self.account2, self.obj1))
        self.assertEquals(True, lockfuncs.self(self.obj1, self.obj1))
        self.assertEquals(True, lockfuncs.self(self.account, self.account))
        self.assertEquals(False, lockfuncs.superuser(self.account, None))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_account_perm(self):
        self.assertEquals(False, lockfuncs.perm(self.account2, None, 'foo'))
        self.assertEquals(False, lockfuncs.perm(self.account2, None, 'Developer'))
        self.assertEquals(False, lockfuncs.perm(self.account2, None, 'Developers'))
        self.assertEquals(True, lockfuncs.perm(self.account2, None, 'Admin'))
        self.assertEquals(True, lockfuncs.perm(self.account2, None, 'Admins'))
        self.assertEquals(True, lockfuncs.perm(self.account2, None, 'Player'))
        self.assertEquals(True, lockfuncs.perm(self.account2, None, 'Players'))
        self.assertEquals(True, lockfuncs.perm(self.account2, None, 'Builder'))
        self.assertEquals(True, lockfuncs.perm(self.account2, None, 'Builders'))
        self.assertEquals(True, lockfuncs.perm_above(self.account2, None, 'Builder'))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_puppet_perm(self):
        self.assertEquals(False, lockfuncs.perm(self.char2, None, 'foo'))
        self.assertEquals(False, lockfuncs.perm(self.char2, None, 'Developer'))
        self.assertEquals(False, lockfuncs.perm(self.char2, None, 'Develoeprs'))
        self.assertEquals(True, lockfuncs.perm(self.char2, None, 'Admin'))
        self.assertEquals(True, lockfuncs.perm(self.char2, None, 'Admins'))
        self.assertEquals(True, lockfuncs.perm(self.char2, None, 'Player'))
        self.assertEquals(True, lockfuncs.perm(self.char2, None, 'Players'))
        self.assertEquals(True, lockfuncs.perm(self.char2, None, 'Builder'))
        self.assertEquals(True, lockfuncs.perm(self.char2, None, 'Builders'))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_account_perm_above(self):
        self.assertEquals(True, lockfuncs.perm_above(self.char2, None, 'Builder'))
        self.assertEquals(True, lockfuncs.perm_above(self.char2, None, 'Builders'))
        self.assertEquals(True, lockfuncs.perm_above(self.char2, None, 'Player'))
        self.assertEquals(False, lockfuncs.perm_above(self.char2, None, 'Admin'))
        self.assertEquals(False, lockfuncs.perm_above(self.char2, None, 'Admins'))
        self.assertEquals(False, lockfuncs.perm_above(self.char2, None, 'Developers'))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_quell_perm(self):
        self.account2.db._quell = True
        self.assertEquals(False, lockfuncs.false(self.char2, None))
        self.assertEquals(False, lockfuncs.perm(self.char2, None, 'Developer'))
        self.assertEquals(False, lockfuncs.perm(self.char2, None, 'Developers'))
        self.assertEquals(False, lockfuncs.perm(self.char2, None, 'Admin'))
        self.assertEquals(False, lockfuncs.perm(self.char2, None, 'Admins'))
        self.assertEquals(True, lockfuncs.perm(self.char2, None, 'Player'))
        self.assertEquals(True, lockfuncs.perm(self.char2, None, 'Players'))
        self.assertEquals(True, lockfuncs.perm(self.char2, None, 'Builder'))
        self.assertEquals(True, lockfuncs.perm(self.char2, None, 'Builders'))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_quell_above_perm(self):
        self.assertEquals(True, lockfuncs.perm_above(self.char2, None, 'Player'))
        self.assertEquals(True, lockfuncs.perm_above(self.char2, None, 'Builder'))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_object_perm(self):
        self.obj2.permissions.add('Admin')
        self.assertEquals(False, lockfuncs.perm(self.obj2, None, 'Developer'))
        self.assertEquals(False, lockfuncs.perm(self.obj2, None, 'Developers'))
        self.assertEquals(True, lockfuncs.perm(self.obj2, None, 'Admin'))
        self.assertEquals(True, lockfuncs.perm(self.obj2, None, 'Admins'))
        self.assertEquals(True, lockfuncs.perm(self.obj2, None, 'Player'))
        self.assertEquals(True, lockfuncs.perm(self.obj2, None, 'Players'))
        self.assertEquals(True, lockfuncs.perm(self.obj2, None, 'Builder'))
        self.assertEquals(True, lockfuncs.perm(self.obj2, None, 'Builders'))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_object_above_perm(self):
        self.obj2.permissions.add('Admin')
        self.assertEquals(False, lockfuncs.perm_above(self.obj2, None, 'Admins'))
        self.assertEquals(True, lockfuncs.perm_above(self.obj2, None, 'Builder'))
        self.assertEquals(True, lockfuncs.perm_above(self.obj2, None, 'Builders'))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_pperm(self):
        self.obj2.permissions.add('Developer')
        self.char2.permissions.add('Developer')
        self.assertEquals(False, lockfuncs.pperm(self.obj2, None, 'Players'))
        self.assertEquals(True, lockfuncs.pperm(self.char2, None, 'Players'))
        self.assertEquals(True, lockfuncs.pperm(self.account, None, 'Admins'))
        self.assertEquals(True, lockfuncs.pperm_above(self.account, None, 'Builders'))
        self.assertEquals(False, lockfuncs.pperm_above(self.account2, None, 'Admins'))
        self.assertEquals(True, lockfuncs.pperm_above(self.char2, None, 'Players'))

    def test_dbref(self):
        dbref = self.obj2.dbref
        self.assertEquals(True, lockfuncs.dbref(self.obj2, None, '%s' % dbref))
        self.assertEquals(False, lockfuncs.id(self.obj2, None, '%s' % (dbref + '1')))
        dbref = self.account2.dbref
        self.assertEquals(True, lockfuncs.pdbref(self.account2, None, '%s' % dbref))
        self.assertEquals(False, lockfuncs.pid(self.account2, None, '%s' % (dbref + '1')))

    def test_attr(self):
        self.obj2.db.testattr = 45
        self.assertEquals(True, lockfuncs.attr(self.obj2, None, 'testattr', '45'))
        self.assertEquals(False, lockfuncs.attr_gt(self.obj2, None, 'testattr', '45'))
        self.assertEquals(True, lockfuncs.attr_ge(self.obj2, None, 'testattr', '45'))
        self.assertEquals(False, lockfuncs.attr_lt(self.obj2, None, 'testattr', '45'))
        self.assertEquals(True, lockfuncs.attr_le(self.obj2, None, 'testattr', '45'))

        self.assertEquals(True, lockfuncs.objattr(None, self.obj2, 'testattr', '45'))
        self.assertEquals(True, lockfuncs.objattr(None, self.obj2, 'testattr', '45'))
        self.assertEquals(False, lockfuncs.objattr(None, self.obj2, 'testattr', '45', compare='lt'))

    def test_locattr(self):
        self.obj2.location.db.locattr = 'test'
        self.assertEquals(True, lockfuncs.locattr(self.obj2, None, 'locattr', 'test'))
        self.assertEquals(False, lockfuncs.locattr(self.obj2, None, 'fail', 'testfail'))
        self.assertEquals(True, lockfuncs.objlocattr(None, self.obj2, 'locattr', 'test'))

    def test_tag(self):
        self.obj2.tags.add("test1")
        self.obj2.tags.add("test2", "category1")
        self.assertEquals(True, lockfuncs.tag(self.obj2, None, 'test1'))
        self.assertEquals(True, lockfuncs.tag(self.obj2, None, 'test2', 'category1'))
        self.assertEquals(False, lockfuncs.tag(self.obj2, None, 'test1', 'category1'))
        self.assertEquals(False, lockfuncs.tag(self.obj2, None, 'test1', 'category2'))
        self.assertEquals(True, lockfuncs.objtag(None, self.obj2, 'test2', 'category1'))
        self.assertEquals(False, lockfuncs.objtag(None, self.obj2, 'test2'))

    def test_inside_holds(self):
        self.assertEquals(True, lockfuncs.inside(self.char1, self.room1))
        self.assertEquals(False, lockfuncs.inside(self.char1, self.room2))
        self.assertEquals(True, lockfuncs.holds(self.room1, self.char1))
        self.assertEquals(False, lockfuncs.holds(self.room2, self.char1))

    def test_has_account(self):
        self.assertEquals(True, lockfuncs.has_account(self.char1, None))
        self.assertEquals(False, lockfuncs.has_account(self.obj1, None))

    @override_settings(IRC_ENABLED=True, TESTVAL=[1, 2, 3])
    def test_serversetting(self):
        # import pudb
        # pudb.set_trace()
        self.assertEquals(True, lockfuncs.serversetting(None, None, 'IRC_ENABLED', 'True'))
        self.assertEquals(True, lockfuncs.serversetting(None, None, 'TESTVAL', '[1, 2, 3]'))
        self.assertEquals(False, lockfuncs.serversetting(None, None, 'TESTVAL', '[1, 2, 4]'))
        self.assertEquals(False, lockfuncs.serversetting(None, None, 'TESTVAL', '123'))
