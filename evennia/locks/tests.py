# -*- coding: utf-8 -*-

"""
This is part of Evennia's unittest framework, for testing
the stability and integrity of the codebase during updates.

This module tests the lock functionality of Evennia.

"""
from evennia.utils.test_resources import EvenniaTest

try:
    # this is a special optimized Django version, only available in current Django devel
    from django.utils.unittest import TestCase
except ImportError:
    from django.test import TestCase

from evennia.locks import lockfuncs

# ------------------------------------------------------------
# Lock testing
# ------------------------------------------------------------


class TestLockCheck(EvenniaTest):
    def testrun(self):
        dbref = self.obj2.dbref
        self.obj1.locks.add("owner:dbref(%s);edit:dbref(%s) or perm(Wizards);examine:perm(Builders) and id(%s);delete:perm(Wizards);get:all()" % (dbref, dbref, dbref))
        self.obj2.permissions.add('Wizards')
        self.assertEquals(True, self.obj1.locks.check(self.obj2, 'owner'))
        self.assertEquals(True, self.obj1.locks.check(self.obj2, 'edit'))
        self.assertEquals(True, self.obj1.locks.check(self.obj2, 'examine'))
        self.assertEquals(True, self.obj1.locks.check(self.obj2, 'delete'))
        self.assertEquals(True, self.obj1.locks.check(self.obj2, 'get'))
        self.obj1.locks.add("get:false()")
        self.assertEquals(False, self.obj1.locks.check(self.obj2, 'get'))
        self.assertEquals(True, self.obj1.locks.check(self.obj2, 'not_exist', default=True))


class TestLockfuncs(EvenniaTest):
    def testrun(self):
        self.obj2.permissions.add('Wizards')
        self.assertEquals(True, lockfuncs.true(self.obj2, self.obj1))
        self.assertEquals(False, lockfuncs.false(self.obj2, self.obj1))
        self.assertEquals(True, lockfuncs.perm(self.obj2, self.obj1, 'Wizards'))
        self.assertEquals(True, lockfuncs.perm_above(self.obj2, self.obj1, 'Builders'))
        dbref = self.obj2.dbref
        self.assertEquals(True, lockfuncs.dbref(self.obj2, self.obj1, '%s' % dbref))
        self.obj2.db.testattr = 45
        self.assertEquals(True, lockfuncs.attr(self.obj2, self.obj1, 'testattr', '45'))
        self.assertEquals(False, lockfuncs.attr_gt(self.obj2, self.obj1, 'testattr', '45'))
        self.assertEquals(True, lockfuncs.attr_ge(self.obj2, self.obj1, 'testattr', '45'))
        self.assertEquals(False, lockfuncs.attr_lt(self.obj2, self.obj1, 'testattr', '45'))
        self.assertEquals(True, lockfuncs.attr_le(self.obj2, self.obj1, 'testattr', '45'))
        self.assertEquals(False, lockfuncs.attr_ne(self.obj2, self.obj1, 'testattr', '45'))
