#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
File: setup.py
Author: Steve Genoud
Date: 2013-08-25
'''
from setuptools import setup
import remarkdown

setup(name='remarkdown',
      version=remarkdown.__version__,
      install_requires=[
          'Parsley>= 1.2',
          'docutils>=0.11'
      ],
      entry_points={'console_scripts': [
          'md2html = remarkdown.scripts:md2html',
          'md2xml = remarkdown.scripts:md2xml',
          'md2pseudoxml = remarkdown.scripts:md2pseudoxml',
          'md2latex = remarkdown.scripts:md2latex',
          'md2xetex = remarkdown.scripts:md2xetex',
      ]},
      packages=['remarkdown']
     )
