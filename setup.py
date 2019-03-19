#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
File: setup.py
Author: Steve Genoud and Luca Barbato
Date: 2014-10-17
"""

from setuptools import setup
import recommonmark


setup(
    name='recommonmark',
    version=recommonmark.__version__,
    description=('A docutils-compatibility bridge to CommonMark, '
                 'enabling you to write CommonMark '
                 'inside of Docutils & Sphinx projects.'),
    url='https://github.com/rtfd/recommonmark',
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
    ],
    install_requires=[
        'commonmark>=0.8.1',
        'docutils>=0.11',
        'sphinx>=1.3.1',
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
