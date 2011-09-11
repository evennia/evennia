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
#      This is a Ruby program! Sorry, couldn't find a Python lib to do this. So if you 
#      don't have Ruby, you need to install that too. 
#      
#      You also need to patch a bug in above program to make multiline code snippets work. 
#      From the same folder as the patch file, apply the patch like this: 
#  
#        patch -p0 -i wiki2html.patch 
#
#   2) Install pandoc (converts from html to reST): 
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
#        wiki2html/ (containing the wiki_converter.rb ruby program (patch applied).)
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

import sys, os, subprocess, re, urllib

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

WIKI_ROOT_URL = "http://code.google.com/p/evennia/wiki/"
WIKI_CRUMB_URL = "/p/evennia/wiki/"

# files to not convert (no file ending)
NO_CONVERT = ["SideBar", "Screenshot"]


#------------------------------------------------------------ 
# This is a version of the importer that imports Google html pages
# directly instead of going through the ruby converter. Alas, while
# being a lot cleaner in implementation, this seems to produce worse
# results in the end (both visually and with broken-link issues), so
# not using it at this time.
#
# See the wiki2html at the bottom for the ruby-version.
#------------------------------------------------------------

def fetch_google_wiki_html_files():
    """
    Acquire wiki html pages from google code 
    """
    # use wiki repo to find html filenames
    html_urls = dict([(re.sub(r"\.wiki", "", fn), WIKI_ROOT_URL + re.sub(r"\.wiki", "?show=content", fn))
                      for fn in os.listdir(WIKI_DIR) if fn.endswith(".wiki")])    

    #html_urls = {"Index":html_urls["Index"]} #SR!

    html_pages = {}
    for name, html_url in html_urls.items():
        print "urllib: fetching %s ..." % html_url
        f = urllib.urlopen(html_url)
        s = f.read()
        s = clean_html(s)
        html_pages[name] = s #clean_html(f.read())
        f.close()

        # saving html file for debugging
        f = open(os.path.join(HTML_DIR, "%s.html" % name), 'w')
        f.write(s)
        f.close()
        
    return html_pages 

def clean_html(htmlstring):
    """
    Clean up html properties special to google code and not known by pandoc    
    """
    # remove wikiheader tag (searches over many lines). Unfortunately python <2.7 don't support 
    # DOTALL flag in re.sub ... 
    matches = re.findall(r'<div id="wikiheader">.*?</div>.*?</div>.*?</div>', htmlstring, re.DOTALL)
    for match in matches:        
        htmlstring = htmlstring.replace(match, "")
    #htmlstring = re.sub(r'<div id="wikiheader">.*?</div>.*?</div>.*?</div>', "", htmlstring, re.DOTALL)
    # remove prefix from urls 
    htmlstring = re.sub('href="' + WIKI_CRUMB_URL, 'href="', htmlstring)
    # remove #links from headers 
    htmlstring = re.sub(r'(<h[0-9]>.*?)(<a href="#.*?</a>)(.*?</h[0-9]>)', r"\1\3", htmlstring)    
    return htmlstring

def html2rest(name, htmlstring):
    """
    Convert html data to reST with pandoc 
    """
    print "pandoc: Converting %s ..." % name
    p = subprocess.Popen([PANDOC_EXE, '--from=html', '--to=rst', '--reference-links'],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    return p.communicate(htmlstring)[0]


def wiki2rest_ver2():
    """
    Convert Google wiki pages to reST. 
    """
    # obtain all html data from google code 
    html_pages = fetch_google_wiki_html_files()
    
    # convert to output files
    for name, htmldata in html_pages.items():
        restfilename = os.path.join(REST_DIR, "%s.rst" % name)
        f = open(restfilename, 'w')
        f.write(html2rest(name, htmldata))
        f.close()
    

#------------------------------------------------------------
# This converter uses the 3rd party ruby script to convert wiki pages
# to html, seems to produce a better final result than downloading html
# directly from google code.
#------------------------------------------------------------

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

        # cleanup of code 
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
        

# main program 
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

