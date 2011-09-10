#! /usr/bin/python 
#
# Auto-generate reST documentation for Sphinx from Evennia source
# code.
# 
# Uses etinenned's sphinx autopackage script. Install it to folder
# "autogen" in this same directory:
#
#   hg clone https://bitbucket.org/etienned/sphinx-autopackage-script autogen
#
# Create a directory tree "code/" containing one directory for every
# package in the PACKAGE dictionary below. Make sure EVENNIA_DIR
# points to an Evennia root dir.  Then just run this script. A new
# folder sphinx/source/code will be created with the reST sources.
#
# Note - this is not working very well at the moment, not all sources
# seems to be properly detected and you get lots of errors when
# compiling. To nevertheless make a link to the code from the doc
# front page, edit docs/sphinx/sources/index.rst to reference
# code/modules.
#


import os, subprocess, shutil

EVENNIA_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

SPHINX_DIR = os.path.join(os.path.join(EVENNIA_DIR, "docs"), "sphinx")
SPHINX_SRC_DIR = os.path.join(SPHINX_DIR, "source")
SPHINX_CODE_DIR = os.path.join(SPHINX_SRC_DIR, "code")

CONVERT_DIR = os.path.join(SPHINX_DIR, 'src2rest')
AUTOGEN_EXE = os.path.join(CONVERT_DIR, os.path.join("autogen", "generate_modules.py"))

def src2rest():
    """
    Run import 
    """
    try:
        shutil.rmtree(SPHINX_CODE_DIR)
        print "Emptied old %s." % SPHINX_CODE_DIR
    except OSError:
        pass 
    os.mkdir(SPHINX_CODE_DIR)
       
    inpath = EVENNIA_DIR
    outpath = SPHINX_CODE_DIR
    excludes = [r".*/migrations/.*", r"evennia\.py$", r"manage\.py$", 
                r"runner\.py$", r"server.py$", r"portal.py$"]
        
    subprocess.call(["python", AUTOGEN_EXE, 
                     "-n", "Evennia",
                     "-d",  outpath,
                     "-s", "rst",
                     "-f",
                     inpath] + excludes)

if __name__ == '__main__':

    try:
        src2rest()
    except Exception, e:
        print e
        print "Make sure to read the header of this file so that it's properly set up."
