#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
File: scripts.py
Author: Steve Genoud
Date: 2013-08-25
Description: Scripts loaded by setuptools entry points
'''


try:
    import locale
    locale.setlocale(locale.LC_ALL, '')
except:
    pass

from docutils.core import publish_cmdline, default_description
from remarkdown.parser import MarkdownParser


def md2html():
    description = ('Generate html document from markdown sources. '
                + default_description)
    publish_cmdline(writer_name='html',
                    parser=MarkdownParser(),
                    description=description)

def md2xml():
    description = ('Generate XML document from markdown sources. '
                + default_description)
    publish_cmdline(writer_name='xml',
                    parser=MarkdownParser(),
                    description=description)
def md2pseudoxml():
    description = ('Generate pseudo-XML document from markdown sources. '
                + default_description)
    publish_cmdline(writer_name='pseudoxml',
                    parser=MarkdownParser(),
                    description=description)

def md2latex():
    description = ('Generate latex document from markdown sources. '
                + default_description)
    publish_cmdline(writer_name='latex',
                    parser=MarkdownParser(),
                    description=description)

def md2xetex():
    description = ('Generate xetex document from markdown sources. '
                + default_description)
    publish_cmdline(writer_name='latex',
                    parser=MarkdownParser(),
                    description=description)

