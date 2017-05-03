
# -*- coding: utf-8 -*-

from recommonmark.parser import CommonMarkParser

templates_path = ['_templates']
source_suffix = '.md'
source_parsers = { '.md': CommonMarkParser }
master_doc = 'index'
project = u'sphinxproj'
copyright = u'2015, rtfd'
author = u'rtfd'
version = '0.1'
release = '0.1'
highlight_language = 'python'
language = None
exclude_patterns = ['_build']
pygments_style = 'sphinx'
todo_include_todos = False
html_theme = 'alabaster'
html_static_path = ['_static']
htmlhelp_basename = 'sphinxproj'
