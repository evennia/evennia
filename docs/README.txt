

EVENNIA DOCUMENTATION
=====================


   - Evennia is extensively documented. Our manual is the
     continuously updating online wiki, 

       https://github.com/evennia/evennia/wiki

   - Snapshots of the manual are also mirrored in reST 
     form to ReadTheDocs:

       http://evennia.readthedocs.org/en/latest/

   - You can also ask for help from the evennia community, 

       http://groups.google.com/group/evennia

   - Or by visiting our irc channel, 

       #evennia on the Freenode network

-------------------
* Doxygen auto-docs 
-------------------

   You can build the developer auto-docs 
   (a fancy searchable index of the entire source tree).
   This makes use of doxygen, a doc generator that parses
   the source tree and creates docs on the fly. 
 
   -  Install doxygen (v1.7+)
  
      Doxygen is available for most platforms from

       http://www.stack.nl/~dimitri/doxygen/ 

      or through your package manager in Linux.

   -  Run   

       doxygen config.dox
 
      This will create the auto-docs in a folder 'html'. 

   -  Start your web browser and point it to 
      
       <evenniadir>/docs/html/index.html 

   -  If you prefer a pdf version for printing, use LaTeX by
      activating the relevant section in config.dox. Run the 
      doxygen command again as above and a new folder 'latex' 
      will be created with the latex sources. You need the 
      LaTeX processing system installed, then enter the new
      latex/ folder and run
      
        make 
     
      This will create the pdf. Be warned however that the pdf 
      docs are many hundreds of pages and the automatic formatting
      of doxygen is not always succeeding.
   
   -  Doxyfile is allows for plenty of configuration to get the 
      docs to look the way you want. You can also output to other 
      formats suitable for various developer environments, Windows 
      help files etc. 

------------------------
* Sphinx Manuals 
------------------------

   If you want to build the reST manuals yourself, you basically need to 
   convert the wiki.  First place yourself in a location where you want 
   to clone the wiki repo to, then clone it:
     
      git clone  https://github.com/evennia/evennia.wiki.git
     
  -   Enter this directory and check out the sphinx branch:
     
          git checkout sphinx
     
      This branch has, apart from all the wiki pages (*.md files), also has a 
      an extra directory sphinx/ that will hold the converted data. 

  -   You need Pandoc for the markdown-to-reST conversion:
     
          http://johnmacfarlane.net/pandoc/installing.html
     
      You need a rather recent version. The versions coming with some linux
      repos are too old to support "github-flavoured markdown" conversion.
      See that page for getting the Haskill build environment in that case.
    
  -   You also need sphinx,
     
          http://sphinx-doc.org/
     
      You can most likely get it with 'pip install sphinx' under Linux. 
     
  -   With all this in place, go to the pylib/ folder and run the
      converter script: 
     
      python update_rest_docs.py
     
      If all goes well, you will see all the wiki pages getting converted.
      The converted *.rst files will end up in the sphinx/ directory. 

  -   Finally, go to sphinx/ and run
     
      make html 
     
      If sphinx is installed, this will create the html files in 
      sphinx/.build. To look at them, point your browser to 
     
      <path-to-wiki-repo>/sphinx/.build/index.html
     
     
