import unittest

class TestMakeIter(unittest.TestCase):
    def test_make_iter(self):
        # self.assertEqual(expected, make_iter(obj))
        assert True # TODO: implement your test here

class TestWrap(unittest.TestCase):
    def test_wrap(self):
        # self.assertEqual(expected, wrap(text, width, **kwargs))
        assert True # TODO: implement your test here

class TestFill(unittest.TestCase):
    def test_fill(self):
        # self.assertEqual(expected, fill(text, width, **kwargs))
        assert True # TODO: implement your test here

class TestCell(unittest.TestCase):
    def test___init__(self):
        # cell = Cell(data, **kwargs)
        assert True # TODO: implement your test here

    def test___str__(self):
        # cell = Cell(data, **kwargs)
        # self.assertEqual(expected, cell.__str__())
        assert True # TODO: implement your test here

    def test___unicode__(self):
        # cell = Cell(data, **kwargs)
        # self.assertEqual(expected, cell.__unicode__())
        assert True # TODO: implement your test here

    def test_get(self):
        # cell = Cell(data, **kwargs)
        # self.assertEqual(expected, cell.get())
        assert True # TODO: implement your test here

    def test_get_height(self):
        # cell = Cell(data, **kwargs)
        # self.assertEqual(expected, cell.get_height())
        assert True # TODO: implement your test here

    def test_get_min_height(self):
        # cell = Cell(data, **kwargs)
        # self.assertEqual(expected, cell.get_min_height())
        assert True # TODO: implement your test here

    def test_get_min_width(self):
        # cell = Cell(data, **kwargs)
        # self.assertEqual(expected, cell.get_min_width())
        assert True # TODO: implement your test here

    def test_get_width(self):
        # cell = Cell(data, **kwargs)
        # self.assertEqual(expected, cell.get_width())
        assert True # TODO: implement your test here

    def test_reformat(self):
        # cell = Cell(data, **kwargs)
        # self.assertEqual(expected, cell.reformat(**kwargs))
        assert True # TODO: implement your test here

    def test_replace_data(self):
        # cell = Cell(data, **kwargs)
        # self.assertEqual(expected, cell.replace_data(data, **kwargs))
        assert True # TODO: implement your test here

class TestEvTable(unittest.TestCase):
    def test___init__(self):
        # ev_table = EvTable(*args, **kwargs)
        assert True # TODO: implement your test here

    def test___str__(self):
        # ev_table = EvTable(*args, **kwargs)
        # self.assertEqual(expected, ev_table.__str__())
        assert True # TODO: implement your test here

    def test___unicode__(self):
        # ev_table = EvTable(*args, **kwargs)
        # self.assertEqual(expected, ev_table.__unicode__())
        assert True # TODO: implement your test here

    def test_add_column(self):
        # ev_table = EvTable(*args, **kwargs)
        # self.assertEqual(expected, ev_table.add_column(*args, **kwargs))
        assert True # TODO: implement your test here

    def test_add_header(self):
        # ev_table = EvTable(*args, **kwargs)
        # self.assertEqual(expected, ev_table.add_header(*args, **kwargs))
        assert True # TODO: implement your test here

    def test_add_row(self):
        # ev_table = EvTable(*args, **kwargs)
        # self.assertEqual(expected, ev_table.add_row(*args, **kwargs))
        assert True # TODO: implement your test here

    def test_get(self):
        # ev_table = EvTable(*args, **kwargs)
        # self.assertEqual(expected, ev_table.get())
        assert True # TODO: implement your test here

    def test_reformat(self):
        # ev_table = EvTable(*args, **kwargs)
        # self.assertEqual(expected, ev_table.reformat(**kwargs))
        assert True # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()
