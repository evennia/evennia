#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
File: setup.py
Author: Steve Genoud and Luca Barbato
Date: 2014-10-17
'''
from setuptools import setup
import recommonmark

setup(name='recommonmark',
      version=recommonmark.__version__,
      install_requires=[
          'commonmark>= 0.5.4',
          'docutils>=0.11'
      ],
      entry_points={'console_scripts': [
          'cm2html = recommonmark.scripts:cm2html',
          'cm2latex = recommonmark.scripts:cm2latex',
          'cm2man = recommonmark.scripts:cm2man',
          'cm2pseudoxml = recommonmark.scripts:cm2pseudoxml',
          'cm2xetex = recommonmark.scripts:cm2xetex',
          'cm2xml = recommonmark.scripts:cm2xml',
      ]},
      packages=['recommonmark']
     )
