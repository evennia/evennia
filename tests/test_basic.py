import unittest

from docutils.core import publish_parts

from recommonmark.parser import CommonMarkParser


class TestStringMethods(unittest.TestCase):

    def test_basic_parser(self):
        source = '# Header'

        ret = publish_parts(
            source=source,
            writer_name='html',
            parser=CommonMarkParser()
        )
        self.assertTrue(ret['title'], 'Header')

if __name__ == '__main__':
    unittest.main()
