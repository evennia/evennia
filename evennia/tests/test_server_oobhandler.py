import unittest

class TestTrackerHandler(unittest.TestCase):
    def test___init__(self):
        # tracker_handler = TrackerHandler(obj)
        assert True # TODO: implement your test here

    def test_add(self):
        # tracker_handler = TrackerHandler(obj)
        # self.assertEqual(expected, tracker_handler.add(fieldname, tracker))
        assert True # TODO: implement your test here

    def test_remove(self):
        # tracker_handler = TrackerHandler(obj)
        # self.assertEqual(expected, tracker_handler.remove(fieldname, trackerclass, *args, **kwargs))
        assert True # TODO: implement your test here

    def test_update(self):
        # tracker_handler = TrackerHandler(obj)
        # self.assertEqual(expected, tracker_handler.update(fieldname, new_value))
        assert True # TODO: implement your test here

class TestTrackerBase(unittest.TestCase):
    def test___init__(self):
        # tracker_base = TrackerBase(*args, **kwargs)
        assert True # TODO: implement your test here

    def test_at_remove(self):
        # tracker_base = TrackerBase(*args, **kwargs)
        # self.assertEqual(expected, tracker_base.at_remove(*args, **kwargs))
        assert True # TODO: implement your test here

    def test_update(self):
        # tracker_base = TrackerBase(*args, **kwargs)
        # self.assertEqual(expected, tracker_base.update(*args, **kwargs))
        assert True # TODO: implement your test here

class TestOOBTicker(unittest.TestCase):
    def test___init__(self):
        # o_ob_ticker = OOBTicker(interval)
        assert True # TODO: implement your test here

class TestOOBHandler(unittest.TestCase):
    def test___init__(self):
        # o_ob_handler = OOBHandler()
        assert True # TODO: implement your test here

    def test_execute_cmd(self):
        # o_ob_handler = OOBHandler()
        # self.assertEqual(expected, o_ob_handler.execute_cmd(session, func_key, *args, **kwargs))
        assert True # TODO: implement your test here

    def test_get_all_tracked(self):
        # o_ob_handler = OOBHandler()
        # self.assertEqual(expected, o_ob_handler.get_all_tracked(session))
        assert True # TODO: implement your test here

    def test_msg(self):
        # o_ob_handler = OOBHandler()
        # self.assertEqual(expected, o_ob_handler.msg(sessid, funcname, *args, **kwargs))
        assert True # TODO: implement your test here

    def test_repeat(self):
        # o_ob_handler = OOBHandler()
        # self.assertEqual(expected, o_ob_handler.repeat(obj, sessid, func_key, interval, *args, **kwargs))
        assert True # TODO: implement your test here

    def test_restore(self):
        # o_ob_handler = OOBHandler()
        # self.assertEqual(expected, o_ob_handler.restore())
        assert True # TODO: implement your test here

    def test_save(self):
        # o_ob_handler = OOBHandler()
        # self.assertEqual(expected, o_ob_handler.save())
        assert True # TODO: implement your test here

    def test_track(self):
        # o_ob_handler = OOBHandler()
        # self.assertEqual(expected, o_ob_handler.track(obj, sessid, fieldname, trackerclass, *args, **kwargs))
        assert True # TODO: implement your test here

    def test_track_attribute(self):
        # o_ob_handler = OOBHandler()
        # self.assertEqual(expected, o_ob_handler.track_attribute(obj, sessid, attr_name, trackerclass))
        assert True # TODO: implement your test here

    def test_track_field(self):
        # o_ob_handler = OOBHandler()
        # self.assertEqual(expected, o_ob_handler.track_field(obj, sessid, field_name, trackerclass))
        assert True # TODO: implement your test here

    def test_unrepeat(self):
        # o_ob_handler = OOBHandler()
        # self.assertEqual(expected, o_ob_handler.unrepeat(obj, sessid, func_key, interval))
        assert True # TODO: implement your test here

    def test_untrack(self):
        # o_ob_handler = OOBHandler()
        # self.assertEqual(expected, o_ob_handler.untrack(obj, sessid, fieldname, trackerclass, *args, **kwargs))
        assert True # TODO: implement your test here

    def test_untrack_attribute(self):
        # o_ob_handler = OOBHandler()
        # self.assertEqual(expected, o_ob_handler.untrack_attribute(obj, sessid, attr_name, trackerclass))
        assert True # TODO: implement your test here

    def test_untrack_field(self):
        # o_ob_handler = OOBHandler()
        # self.assertEqual(expected, o_ob_handler.untrack_field(obj, sessid, field_name))
        assert True # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()
