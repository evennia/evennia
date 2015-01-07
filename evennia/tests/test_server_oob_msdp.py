import unittest

class TestOOBFieldTracker(unittest.TestCase):
    def test___init__(self):
        # o_ob_field_tracker = OOBFieldTracker(oobhandler, fieldname, sessid, *args, **kwargs)
        assert True # TODO: implement your test here

    def test_update(self):
        # o_ob_field_tracker = OOBFieldTracker(oobhandler, fieldname, sessid, *args, **kwargs)
        # self.assertEqual(expected, o_ob_field_tracker.update(new_value, *args, **kwargs))
        assert True # TODO: implement your test here

class TestOOBAttributeTracker(unittest.TestCase):
    def test___init__(self):
        # o_ob_attribute_tracker = OOBAttributeTracker(oobhandler, fieldname, sessid, attrname, *args, **kwargs)
        assert True # TODO: implement your test here

    def test_update(self):
        # o_ob_attribute_tracker = OOBAttributeTracker(oobhandler, fieldname, sessid, attrname, *args, **kwargs)
        # self.assertEqual(expected, o_ob_attribute_tracker.update(new_value, *args, **kwargs))
        assert True # TODO: implement your test here

class TestOobError(unittest.TestCase):
    def test_oob_error(self):
        # self.assertEqual(expected, oob_error(oobhandler, session, errmsg, *args, **kwargs))
        assert True # TODO: implement your test here

class TestList(unittest.TestCase):
    def test_list(self):
        # self.assertEqual(expected, list(oobhandler, session, mode, *args, **kwargs))
        assert True # TODO: implement your test here

class TestSend(unittest.TestCase):
    def test_send(self):
        # self.assertEqual(expected, send(oobhandler, session, *args, **kwargs))
        assert True # TODO: implement your test here

class TestReport(unittest.TestCase):
    def test_report(self):
        # self.assertEqual(expected, report(oobhandler, session, *args, **kwargs))
        assert True # TODO: implement your test here

class TestUnreport(unittest.TestCase):
    def test_unreport(self):
        # self.assertEqual(expected, unreport(oobhandler, session, vartype, *args, **kwargs))
        assert True # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()
