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
from recommonmark.parser import CommonMarkParser


def cm2html():
    description = ('Generate html document from markdown sources. ' + default_description)
    publish_cmdline(writer_name='html',
                    parser=CommonMarkParser(),
                    description=description)


def cm2man():
    description = ('Generate a manpage from markdown sources. ' + default_description)
    publish_cmdline(writer_name='manpage',
                    parser=CommonMarkParser(),
                    description=description)


def cm2xml():
    description = ('Generate XML document from markdown sources. ' + default_description)
    publish_cmdline(writer_name='xml',
                    parser=CommonMarkParser(),
                    description=description)


def cm2pseudoxml():
    description = ('Generate pseudo-XML document from markdown sources. ' + default_description)
    publish_cmdline(writer_name='pseudoxml',
                    parser=CommonMarkParser(),
                    description=description)


def cm2latex():
    description = ('Generate latex document from markdown sources. ' + default_description)
    publish_cmdline(writer_name='latex',
                    parser=CommonMarkParser(),
                    description=description)


def cm2xetex():
    description = ('Generate xetex document from markdown sources. ' + default_description)
    publish_cmdline(writer_name='latex',
                    parser=CommonMarkParser(),
                    description=description)
