# -*- coding: utf-8 -*-

import unittest
from textwrap import dedent

from docutils import nodes
from docutils.utils import new_document
from docutils.readers import Reader
from docutils.core import publish_parts

from CommonMark import Parser
from recommonmark.parser import CommonMarkParser


class TestParsing(unittest.TestCase):

    def assertParses(self, source, expected, alt=False):  # noqa
        parser = CommonMarkParser()
        parser.parse(dedent(source), new_document('<string>'))
        self.assertMultiLineEqual(
            dedent(expected).lstrip(),
            dedent(parser.document.asdom().toprettyxml(indent='  ')),
        )

    def test_heading(self):
        self.assertParses(
            """
            # Heading 1

            ## Heading 2

            Body
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <section ids="heading-1" names="heading\ 1">
                <title>Heading 1</title>
                <section ids="heading-2" names="heading\ 2">
                  <title>Heading 2</title>
                  <paragraph>Body</paragraph>
                </section>
              </section>
            </document>
            """
        )

    def test_heading_inline(self):
        self.assertParses(
            """# Heading *foo*""",
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <section ids="heading-foo" names="heading\ foo">
                <title>
                  Heading \n\
                  <emphasis>foo</emphasis>
                </title>
              </section>
            </document>
            """
        )

    def test_paragraph(self):
        self.assertParses(
            """This is a paragraph""",
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>This is a paragraph</paragraph>
            </document>
            """
        )
        self.assertParses(
            """This is a paragraph *foo***bar**""",
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>
                This is a paragraph \n\
                <emphasis>foo</emphasis>
                <strong>bar</strong>
              </paragraph>
            </document>
            """
        )
        self.assertParses(
            """
            This is a paragraph
            This is a new line
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>
                This is a paragraph


                This is a new line
              </paragraph>
            </document>
            """
        )

    def test_entities(self):
        self.assertParses(
            u"""
            &copy;
            """,
            u"""
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>©</paragraph>
            </document>
            """
        )

    def test_links(self):
        self.assertParses(
            """
            This is a [link](http://example.com)
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>
                This is a \n\
                <reference refuri="http://example.com">link</reference>
              </paragraph>
            </document>
            """
        )
        self.assertParses(
            """
            This is a [link][example]

            [example]: http://example.com "Example"
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>
                This is a \n\
                <reference refuri="http://example.com" title="Example">link</reference>
              </paragraph>
            </document>
            """
        )
        self.assertParses(
            """
            This is a [link][example]

            [example]: http://example.com
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>
                This is a \n\
                <reference refuri="http://example.com">link</reference>
              </paragraph>
            </document>
            """
        )
        self.assertParses(
            """
            <http://example.com>
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>
                <reference refuri="http://example.com">http://example.com</reference>
              </paragraph>
            </document>
            """
        )
        self.assertParses(
            """
            [link](/foo)
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>
                <pending_xref refexplicit="True" reftarget="/foo" reftype="any" refwarn="True">
                  <reference refuri="/foo">link</reference>
                </pending_xref>
              </paragraph>
            </document>
            """
        )
        self.assertParses(
            """
            [link](foo)
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>
                <pending_xref refexplicit="True" reftarget="foo" reftype="any" refwarn="True">
                  <reference refuri="foo">link</reference>
                </pending_xref>
              </paragraph>
            </document>
            """
        )

    def test_image(self):
        self.assertParses(
            """
            ![foo](/url "title")
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>
                <image alt="title" uri="/url">foo</image>
              </paragraph>
            </document>
            """
        )

    def test_inline_code(self):
        self.assertParses(
            """
            This is `code` right?
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>
                This is \n\
                <literal>code</literal>
                 right?
              </paragraph>
            </document>
            """
        )

    def test_bullet_list(self):
        self.assertParses(
            """
            * List item 1
            * List item 2
            * List item 3
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <bullet_list>
                <list_item>
                  <paragraph>List item 1</paragraph>
                </list_item>
                <list_item>
                  <paragraph>List item 2</paragraph>
                </list_item>
                <list_item>
                  <paragraph>List item 3</paragraph>
                </list_item>
              </bullet_list>
            </document>
            """
        )
        self.assertParses(
            """
            * [List item 1](/1)
            * [List item 2](/2)
            * [List item 3](/3)
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <bullet_list>
                <list_item>
                  <paragraph>
                    <pending_xref refexplicit="True" reftarget="/1" reftype="any" refwarn="True">
                      <reference refuri="/1">List item 1</reference>
                    </pending_xref>
                  </paragraph>
                </list_item>
                <list_item>
                  <paragraph>
                    <pending_xref refexplicit="True" reftarget="/2" reftype="any" refwarn="True">
                      <reference refuri="/2">List item 2</reference>
                    </pending_xref>
                  </paragraph>
                </list_item>
                <list_item>
                  <paragraph>
                    <pending_xref refexplicit="True" reftarget="/3" reftype="any" refwarn="True">
                      <reference refuri="/3">List item 3</reference>
                    </pending_xref>
                  </paragraph>
                </list_item>
              </bullet_list>
            </document>
            """
        )

    def test_enumerated_list(self):
        self.assertParses(
            """
            1. List item 1
            2. List item 2
            3. List item 3
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <enumerated_list>
                <list_item>
                  <paragraph>List item 1</paragraph>
                </list_item>
                <list_item>
                  <paragraph>List item 2</paragraph>
                </list_item>
                <list_item>
                  <paragraph>List item 3</paragraph>
                </list_item>
              </enumerated_list>
            </document>
            """
        )

    def test_code(self):
        self.assertParses(
            """
            Code:

                #!/bin/sh
                python
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>Code:</paragraph>
              <literal_block xml:space="preserve">#!/bin/sh
            python</literal_block>
            </document>
            """
        )

    def test_block_quote(self):
        self.assertParses(
            """
            > Here is a quoted list:
            > \n\
            > * Item 1
            > * Item 2
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <block_quote>
                <paragraph>Here is a quoted list:</paragraph>
                <bullet_list>
                  <list_item>
                    <paragraph>Item 1</paragraph>
                  </list_item>
                  <list_item>
                    <paragraph>Item 2</paragraph>
                  </list_item>
                </bullet_list>
              </block_quote>
            </document>
            """
        )

    def test_horizontal_rule(self):
        self.assertParses(
            """
            Foo

            ----

            Bar
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>Foo</paragraph>
              <transition/>
              <paragraph>Bar</paragraph>
            </document>
            """
        )

    def test_html(self):
        self.assertParses(
            """
            Foo

            <blink>Blink</blink>
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <paragraph>Foo</paragraph>
              <paragraph>
                <raw format="html" xml:space="preserve">&lt;blink&gt;</raw>
                Blink
                <raw format="html" xml:space="preserve">&lt;/blink&gt;</raw>
              </paragraph>
            </document>
            """
        )

    def test_eval(self):
        self.assertParses(
            """
            ```eval_rst
            .. image:: figure.png
            ```
            """,
            """
            <?xml version="1.0" ?>
            <document source="&lt;string&gt;">
              <literal_block language="eval_rst" xml:space="preserve">\
.. image:: figure.png</literal_block>
            </document>
            """
        )


if __name__ == '__main__':
    unittest.main()
