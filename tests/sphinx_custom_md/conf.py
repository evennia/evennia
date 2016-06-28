
# -*- coding: utf-8 -*-

from recommonmark.parser import CommonMarkParser
from recommonmark.transform import AutoStructify

templates_path = ['_templates']
source_suffix = '.markdown'
source_parsers = { '.markdown': CommonMarkParser }
master_doc = 'index'
project = u'sphinxproj'
copyright = u'2015, rtfd'
author = u'rtfd'
version = '0.1'
release = '0.1'
language = None
exclude_patterns = ['_build']
highlight_language = 'python'
pygments_style = 'sphinx'
todo_include_todos = False
html_theme = 'alabaster'
html_static_path = ['_static']
htmlhelp_basename = 'sphinxproj'

def setup(app):
    app.add_config_value('recommonmark_config', {
            'enable_eval_rst': True,
            'commonmark_suffixes': ['.markdown', '.hpp'],
            }, True)
    app.add_transform(AutoStructify)
