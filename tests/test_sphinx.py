import os
import io
import sys
import shutil
import unittest

from sphinx.application import Sphinx


class SphinxIntegrationTests(unittest.TestCase):

    def _run_test(self, test_dir, test_file, test_strings):
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
                text = fin.read().strip()
                for test_string in test_strings:
                    self.assertIn(test_string, text)
        finally:
            shutil.rmtree('_build')
            os.chdir('../..')

class CodeBlockTests(SphinxIntegrationTests):

    def test_integration(self):
        self._run_test(
            'sphinx_code_block',
            '_build/text/index.html',
            ['<div class="highlight">']
        )


class IndentedCodeTests(SphinxIntegrationTests):

    def test_integration(self):
        self._run_test(
            'sphinx_indented_code',
            '_build/text/index.html',
            ['<div class="highlight">']
        )

class CustomExtensionTests(SphinxIntegrationTests):

    def test_integration(self):
        self._run_test(
            'sphinx_custom_md',
            '_build/text/index.html',
            ['</table>']
        )

class XrefTests(SphinxIntegrationTests):

    def test_integration(self):
        self._run_test(
            'sphinx_xref',
            '_build/text/index.html',
            ['href="link.html"', 'href="http://www.google.com"']
        )
