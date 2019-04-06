import os
import io
import sys
import shutil
import unittest
from contextlib import contextmanager

from sphinx.application import Sphinx


@contextmanager
def sphinx_built_file(test_dir, test_file):
    os.chdir('tests/{0}'.format(test_dir))
    try:
        app = Sphinx(
            srcdir='.',
            confdir='.',
            outdir='_build/text',
            doctreedir='_build/.doctrees',
            buildername='html',
            verbosity=1,
        )
        app.build(force_all=True)
        with io.open(test_file, encoding='utf-8') as fin:
            yield fin.read().strip()
    finally:
        shutil.rmtree('_build')
        os.chdir('../..')


def run_test(test_dir, test_file, test_string):
    with sphinx_built_file(test_dir, test_file) as output:
        assert test_string in output


class SphinxIntegrationTests(unittest.TestCase):

    build_path = None

    def setUp(self):
        if self.build_path is not None:
            self.app = Sphinx(
                srcdir=self.build_path,
                confdir=self.build_path,
                outdir=os.path.join(self.build_path, '_build', 'text'),
                doctreedir=os.path.join(self.build_path, '_build', '.doctrees'),
                buildername='html',
                verbosity=1,
            )
            self.app.build(force_all=True)

    def tearDown(self):
        if self.build_path is not None:
            shutil.rmtree(os.path.join(self.build_path, '_build'))

    def read_file(self, path):
        full_path = os.path.join(self.build_path, '_build', 'text', path)
        with io.open(full_path, encoding='utf-8') as h:
            return h.read().strip()


class GenericTests(SphinxIntegrationTests):

    build_path = 'tests/sphinx_generic'

    def test_headings(self):
        output = self.read_file('index.html')
        self.assertIn(
            ('<h1>Heading 1'
             '<a class="headerlink" '
             'href="#heading-1" '
             u'title="Permalink to this headline">\xb6</a>'
             '</h1>'),
            output,
        )
        self.assertIn(
            ('<h2>Heading 2'
             '<a class="headerlink" '
             'href="#heading-2" '
             u'title="Permalink to this headline">\xb6</a>'
             '</h2>'),
            output,
        )
        self.assertIn(
            ('<h3>Heading 3'
             '<a class="headerlink" '
             'href="#heading-3" '
             u'title="Permalink to this headline">\xb6</a>'
             '</h3>'),
            output,
        )
        self.assertIn(
            ('<h4>Heading 4'
             '<a class="headerlink" '
             'href="#heading-4" '
             u'title="Permalink to this headline">\xb6</a>'
             '</h4>'),
            output,
        )

    def test_links(self):
        output = self.read_file('index.html')
        self.assertIn(
            ('This is a '
             '<a class="reference external" '
             'href="http://example.com">link</a>'),
            output
        )
        self.assertIn(
            ('This is a '
             '<a class="reference external" '
             'href="http://example.com/foobar">ref link</a>'),
            output
        )
        self.assertIn(
            ('This is a '
             '<a class="reference external" '
             'href="/example">relative link</a>'),
            output
        )
        self.assertIn(
            ('This is a '
             '<a class="reference internal" href="#">'
             '<span class="doc">pending ref</span>'
             '</a>'),
            output
        )

    def test_image(self):
        output = self.read_file('index.html')
        self.assertIn(
            '<p><img alt="foo &quot;handle quotes&quot;" src="image.png" /></p>',
            output
        )

    def test_paragraph(self):
        output = self.read_file('index.html')
        self.assertIn('<p>Foo</p>', output)
        self.assertIn('<p>Bar</p>', output)

    def test_lists(self):
        output = self.read_file('index.html')
        self.assertIn(
            ('<ul class="simple">\n'
             '<li>Item A</li>\n'
             '<li>Item B</li>\n'
             '<li>Item C</li>\n'
             '</ul>'),
            output
        )
        self.assertIn(
            ('<ol class="simple">\n'
             '<li>Item 1</li>\n'
             '<li>Item 2</li>\n'
             '<li>Item 3</li>\n'
             '</ol>'),
            output
        )

    def test_code(self):
        output = self.read_file('index.html')
        self.assertIn(
            ('<pre><span></span>'
             '<span class="ch">#!/bin/sh</span>\n'
             '<span class="n">python</span>\n'
             '</pre>'),
            output
        )

    def test_thematic_break(self):
        output = self.read_file('index.html')
        self.assertIn(
            '<p>Foo</p>\n<hr class="docutils" />\n<p>Bar</p>',
            output
        )


class CodeBlockTests(unittest.TestCase):

    def test_integration(self):
        with sphinx_built_file('sphinx_code_block', '_build/text/index.html') as output:
            self.assertIn('<div class="highlight">', output)


class IndentedCodeTests(unittest.TestCase):

    def test_integration(self):
        run_test(
            'sphinx_indented_code',
            '_build/text/index.html',
            '<div class="highlight">'
        )

class NestedHeaderBlock(unittest.TestCase):

    def test_integration(self):
        run_test(
            'sphinx_nested_header_block',
            '_build/text/index.html',
            '<h1>'
        )

class CustomExtensionTests(SphinxIntegrationTests):

    build_path = 'tests/sphinx_custom_md'

    def test_integration(self):
        output = self.read_file('index.html')
        self.assertIn('<table ', output)
        self.assertIn('<th class="head">abc</th>', output)
        self.assertIn('<th class="head">data</th>', output)
        self.assertIn('</table>', output)

        self.assertIn(
            ('<div class="contents topic" id="contents">\n'
             '<p class="topic-title first">Contents</p>\n'
             '<ul class="simple">\n'
             '<li><a class="reference internal" href="#header" id="id1">Header</a><ul>\n'
             '<li><a class="reference internal" href="#header-2" id="id2">Header 2</a></li>\n'
             '</ul>\n</li>\n</ul>'),
            output
            )
