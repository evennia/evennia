#! /usr/bin/python 
#
#  Converts Evennia's google-style wiki pages to reST documents
#
#  Setting up to run: 
#
#   1) From this directory, use SVN to download wiki2html converter by Chris Roos. Make sure 
#      to download into a directory "wiki2html" like this: 
#
#        svn co http://chrisroos.googlecode.com/svn/trunk/google-wiki-syntax wiki2html
#
#      This is a ruby program! Sorry, it was the best match I could find to do this. 
#      So if you don't have ruby, you need that too. 
#
#   2) Install pandoc: 
#
#        apt-get install pandoc  (debian)
#           or download from 
#        http://johnmacfarlane.net/pandoc/
#
#   3) Retrieve wiki files (*.wiki) from Google code by mercurial. Make sure
#      to retrieve them into a directory wikiconvert/wiki: 
#
#         hg clone https://code.google.com/p/evennia.wiki wiki
#
#   4) Check so that you have the following file structure: 
#
#        wiki/ (containing google code wiki files)
#        wiki2html/ (containing the wiki_converter.rb ruby program.)
#        html/  (empty)
#        rest/  (empty)
#        (this file)
#
#   Usage: 
#
#   1) Pull the wiki files into wiki/ so you have the latest. 
#   2) Run wiki2rest.py. Folders html and rest will end up containing the conversions and the contents 
#      of rest/ will automatically be copied over to docs/sphinx/source/wiki. 
#

import sys, os, subprocess, re

# Setup

EVENNIA_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


SPHINX_DIR = os.path.join(os.path.join(EVENNIA_DIR, "docs"), "sphinx")
SPHINX_SRC_DIR = os.path.join(SPHINX_DIR, "source")
SPHINX_WIKI_DIR = os.path.join(SPHINX_SRC_DIR, "wiki")
CONVERT_DIR = os.path.join(SPHINX_DIR, "wiki2rest")

WIKI_DIR = os.path.join(CONVERT_DIR, "wiki")
HTML_DIR = os.path.join(CONVERT_DIR, "html")
REST_DIR = os.path.join(CONVERT_DIR, "rest")
WIKI2HTML_DIR = os.path.join(CONVERT_DIR, "wiki2html")
PANDOC_EXE = "pandoc"
RUBY_EXE = "ruby"

# files to not convert (no file ending)
NO_CONVERT = ["SideBar", "Screenshot"]


def wiki2rest():
    """
    Convert from wikifile to rst file, going through html 
    """        

    # convert from wikifile to html with wiki2html
    subprocess.call([RUBY_EXE, "wiki_convertor.rb", WIKI_DIR, HTML_DIR], cwd=WIKI2HTML_DIR)

    # convert from html to rest with pandoc
    htmlfilenames = [fn for fn in os.listdir(HTML_DIR) 
                     if fn.endswith(".html") and not re.sub(r".html", "", fn) in NO_CONVERT]

    for filename in htmlfilenames: 

        htmlfilename = os.path.join(HTML_DIR, filename)

        string = "".join(open(htmlfilename, 'r').readlines())        
        string = re.sub(r'<p class="summary">[A-Za-z0-9 .-\:]*</p>', "", string)
        string = re.sub(r"&lt;wiki:toc max_depth=&quot;[0-9]*&quot; /&gt;", "", string)            
        string = re.sub(r"&lt;wiki:toc max_depth<h1>&quot;[0-9]*&quot; /&gt;</h1>", "", string)            
        string = re.sub(r"<p>#settings Featured</p>", "", string)
        string = re.sub(r'<p class="labels">Featured</p>', "", string)
        string = re.sub(r'&lt;wiki:comment&gt;', "", string)
        string = re.sub(r'&lt;/wiki:comment&gt;', "", string)
        #string = re.sub(r'&lt;wiki:comment&gt;[<>;a-zA\/\n-&Z0-9 ]*&lt;/wiki:comment&gt;', "", string)
        f = open(htmlfilename, 'w')
        f.write(string)
        f.close()

        rstfilename = os.path.join(REST_DIR, re.sub(r".html$", ".rst", filename))
        print "pandoc: converting %s -> %s" % (htmlfilename, rstfilename)
        subprocess.call([PANDOC_EXE, "--from=html", "--to=rst", "-o", rstfilename, htmlfilename])
        
if __name__ == "__main__":

    try:
        wiki2rest() 
    except Exception, e:
        print e
        print "Make sure to read this file's header to make sure everything is correctly set up. "
        sys.exit()

    import shutil
    try:
        shutil.rmtree(SPHINX_WIKI_DIR)
        print "Deleted old %s." % SPHINX_WIKI_DIR
    except OSError:
        pass 
    print "Copying %s -> %s" % (REST_DIR, SPHINX_WIKI_DIR)
    shutil.copytree(REST_DIR, SPHINX_WIKI_DIR)

