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
        self.obj1.locks.add(
            "owner:dbref(%s);edit:dbref(%s) or perm(Admin);examine:perm(Builder) "
            "and id(%s);delete:perm(Admin);get:all()" % (dbref, dbref, dbref)
        )
        self.obj2.permissions.add("Admin")
        self.assertEqual(True, self.obj1.locks.check(self.obj2, "owner"))
        self.assertEqual(True, self.obj1.locks.check(self.obj2, "edit"))
        self.assertEqual(True, self.obj1.locks.check(self.obj2, "examine"))
        self.assertEqual(True, self.obj1.locks.check(self.obj2, "delete"))
        self.assertEqual(True, self.obj1.locks.check(self.obj2, "get"))
        self.obj1.locks.add("get:false()")
        self.assertEqual(False, self.obj1.locks.check(self.obj2, "get"))
        self.assertEqual(True, self.obj1.locks.check(self.obj2, "not_exist", default=True))


class TestLockfuncs(EvenniaTest):
    def setUp(self):
        super(TestLockfuncs, self).setUp()
        self.account2.permissions.add("Admin")
        self.char2.permissions.add("Builder")

    def test_booleans(self):
        self.assertEqual(True, lockfuncs.true(self.account2, self.obj1))
        self.assertEqual(True, lockfuncs.all(self.account2, self.obj1))
        self.assertEqual(False, lockfuncs.false(self.account2, self.obj1))
        self.assertEqual(False, lockfuncs.none(self.account2, self.obj1))
        self.assertEqual(True, lockfuncs.self(self.obj1, self.obj1))
        self.assertEqual(True, lockfuncs.self(self.account, self.account))
        self.assertEqual(False, lockfuncs.superuser(self.account, None))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_account_perm(self):
        self.assertEqual(False, lockfuncs.perm(self.account2, None, "foo"))
        self.assertEqual(False, lockfuncs.perm(self.account2, None, "Developer"))
        self.assertEqual(False, lockfuncs.perm(self.account2, None, "Developers"))
        self.assertEqual(True, lockfuncs.perm(self.account2, None, "Admin"))
        self.assertEqual(True, lockfuncs.perm(self.account2, None, "Admins"))
        self.assertEqual(True, lockfuncs.perm(self.account2, None, "Player"))
        self.assertEqual(True, lockfuncs.perm(self.account2, None, "Players"))
        self.assertEqual(True, lockfuncs.perm(self.account2, None, "Builder"))
        self.assertEqual(True, lockfuncs.perm(self.account2, None, "Builders"))
        self.assertEqual(True, lockfuncs.perm_above(self.account2, None, "Builder"))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_puppet_perm(self):
        self.assertEqual(False, lockfuncs.perm(self.char2, None, "foo"))
        self.assertEqual(False, lockfuncs.perm(self.char2, None, "Developer"))
        self.assertEqual(False, lockfuncs.perm(self.char2, None, "Develoeprs"))
        self.assertEqual(True, lockfuncs.perm(self.char2, None, "Admin"))
        self.assertEqual(True, lockfuncs.perm(self.char2, None, "Admins"))
        self.assertEqual(True, lockfuncs.perm(self.char2, None, "Player"))
        self.assertEqual(True, lockfuncs.perm(self.char2, None, "Players"))
        self.assertEqual(True, lockfuncs.perm(self.char2, None, "Builder"))
        self.assertEqual(True, lockfuncs.perm(self.char2, None, "Builders"))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_account_perm_above(self):
        self.assertEqual(True, lockfuncs.perm_above(self.char2, None, "Builder"))
        self.assertEqual(True, lockfuncs.perm_above(self.char2, None, "Builders"))
        self.assertEqual(True, lockfuncs.perm_above(self.char2, None, "Player"))
        self.assertEqual(False, lockfuncs.perm_above(self.char2, None, "Admin"))
        self.assertEqual(False, lockfuncs.perm_above(self.char2, None, "Admins"))
        self.assertEqual(False, lockfuncs.perm_above(self.char2, None, "Developers"))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_quell_perm(self):
        self.account2.db._quell = True
        self.assertEqual(False, lockfuncs.false(self.char2, None))
        self.assertEqual(False, lockfuncs.perm(self.char2, None, "Developer"))
        self.assertEqual(False, lockfuncs.perm(self.char2, None, "Developers"))
        self.assertEqual(False, lockfuncs.perm(self.char2, None, "Admin"))
        self.assertEqual(False, lockfuncs.perm(self.char2, None, "Admins"))
        self.assertEqual(True, lockfuncs.perm(self.char2, None, "Player"))
        self.assertEqual(True, lockfuncs.perm(self.char2, None, "Players"))
        self.assertEqual(True, lockfuncs.perm(self.char2, None, "Builder"))
        self.assertEqual(True, lockfuncs.perm(self.char2, None, "Builders"))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_quell_above_perm(self):
        self.assertEqual(True, lockfuncs.perm_above(self.char2, None, "Player"))
        self.assertEqual(True, lockfuncs.perm_above(self.char2, None, "Builder"))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_object_perm(self):
        self.obj2.permissions.add("Admin")
        self.assertEqual(False, lockfuncs.perm(self.obj2, None, "Developer"))
        self.assertEqual(False, lockfuncs.perm(self.obj2, None, "Developers"))
        self.assertEqual(True, lockfuncs.perm(self.obj2, None, "Admin"))
        self.assertEqual(True, lockfuncs.perm(self.obj2, None, "Admins"))
        self.assertEqual(True, lockfuncs.perm(self.obj2, None, "Player"))
        self.assertEqual(True, lockfuncs.perm(self.obj2, None, "Players"))
        self.assertEqual(True, lockfuncs.perm(self.obj2, None, "Builder"))
        self.assertEqual(True, lockfuncs.perm(self.obj2, None, "Builders"))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_object_above_perm(self):
        self.obj2.permissions.add("Admin")
        self.assertEqual(False, lockfuncs.perm_above(self.obj2, None, "Admins"))
        self.assertEqual(True, lockfuncs.perm_above(self.obj2, None, "Builder"))
        self.assertEqual(True, lockfuncs.perm_above(self.obj2, None, "Builders"))

    @override_settings(PERMISSION_HIERARCHY=settings_default.PERMISSION_HIERARCHY)
    def test_pperm(self):
        self.obj2.permissions.add("Developer")
        self.char2.permissions.add("Developer")
        self.assertEqual(False, lockfuncs.pperm(self.obj2, None, "Players"))
        self.assertEqual(True, lockfuncs.pperm(self.char2, None, "Players"))
        self.assertEqual(True, lockfuncs.pperm(self.account, None, "Admins"))
        self.assertEqual(True, lockfuncs.pperm_above(self.account, None, "Builders"))
        self.assertEqual(False, lockfuncs.pperm_above(self.account2, None, "Admins"))
        self.assertEqual(True, lockfuncs.pperm_above(self.char2, None, "Players"))

    def test_dbref(self):
        dbref = self.obj2.dbref
        self.assertEqual(True, lockfuncs.dbref(self.obj2, None, "%s" % dbref))
        self.assertEqual(False, lockfuncs.id(self.obj2, None, "%s" % (dbref + "1")))
        dbref = self.account2.dbref
        self.assertEqual(True, lockfuncs.pdbref(self.account2, None, "%s" % dbref))
        self.assertEqual(False, lockfuncs.pid(self.account2, None, "%s" % (dbref + "1")))

    def test_attr(self):
        self.obj2.db.testattr = 45
        self.assertEqual(True, lockfuncs.attr(self.obj2, None, "testattr", "45"))
        self.assertEqual(False, lockfuncs.attr_gt(self.obj2, None, "testattr", "45"))
        self.assertEqual(True, lockfuncs.attr_ge(self.obj2, None, "testattr", "45"))
        self.assertEqual(False, lockfuncs.attr_lt(self.obj2, None, "testattr", "45"))
        self.assertEqual(True, lockfuncs.attr_le(self.obj2, None, "testattr", "45"))

        self.assertEqual(True, lockfuncs.objattr(None, self.obj2, "testattr", "45"))
        self.assertEqual(True, lockfuncs.objattr(None, self.obj2, "testattr", "45"))
        self.assertEqual(False, lockfuncs.objattr(None, self.obj2, "testattr", "45", compare="lt"))

    def test_locattr(self):
        self.obj2.location.db.locattr = "test"
        self.assertEqual(True, lockfuncs.locattr(self.obj2, None, "locattr", "test"))
        self.assertEqual(False, lockfuncs.locattr(self.obj2, None, "fail", "testfail"))
        self.assertEqual(True, lockfuncs.objlocattr(None, self.obj2, "locattr", "test"))

    def test_tag(self):
        self.obj2.tags.add("test1")
        self.obj2.tags.add("test2", "category1")
        self.assertEqual(True, lockfuncs.tag(self.obj2, None, "test1"))
        self.assertEqual(True, lockfuncs.tag(self.obj2, None, "test2", "category1"))
        self.assertEqual(False, lockfuncs.tag(self.obj2, None, "test1", "category1"))
        self.assertEqual(False, lockfuncs.tag(self.obj2, None, "test1", "category2"))
        self.assertEqual(True, lockfuncs.objtag(None, self.obj2, "test2", "category1"))
        self.assertEqual(False, lockfuncs.objtag(None, self.obj2, "test2"))

    def test_inside_holds(self):
        self.assertEqual(True, lockfuncs.inside(self.char1, self.room1))
        self.assertEqual(False, lockfuncs.inside(self.char1, self.room2))
        self.assertEqual(True, lockfuncs.holds(self.room1, self.char1))
        self.assertEqual(False, lockfuncs.holds(self.room2, self.char1))

    def test_has_account(self):
        self.assertEqual(True, lockfuncs.has_account(self.char1, None))
        self.assertEqual(False, lockfuncs.has_account(self.obj1, None))

    @override_settings(IRC_ENABLED=True, TESTVAL=[1, 2, 3])
    def test_serversetting(self):
        self.assertEqual(True, lockfuncs.serversetting(None, None, "IRC_ENABLED", "True"))
        self.assertEqual(True, lockfuncs.serversetting(None, None, "TESTVAL", "[1, 2, 3]"))
        self.assertEqual(False, lockfuncs.serversetting(None, None, "TESTVAL", "[1, 2, 4]"))
        self.assertEqual(False, lockfuncs.serversetting(None, None, "TESTVAL", "123"))
