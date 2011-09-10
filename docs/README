
===========
DOCS README
===========

* Evennia docs and manual 

   - The most updated documentation is found in the online wiki, 

       http://code.google.com/p/evennia/wiki/Index
   
   - You can also ask for help from the evennia community, 

       http://groups.google.com/group/evennia

   - Or by visiting our irc channel, 

       #evennia on the Freenode network


------------------------
* Sphinx Manuals 
------------------------

  The folder docs/sphinx contains a source tree with Evennia's online wiki
  formatted into reStructuredText for easy (and good looking!) offline 
  browsing or printing. 

  To build the sources you need to install Sphinx. Linux users can get it 
  through their package managers (in Debian it's called python-sphinx). Or
  you can download it here: 

     http://sphinx.pocoo.org/index.html

  Go into docs/sphinx and run 

     make html

  You will see a lot of output (and probably some errors too, Evennia's docs
  are not formatted to reST format by default). When done, point your 
  web browser to docs/sphinx/build/html/index.html to see the nice manual.
  
  If you don't want html output, you can output to a host of other formats,
  use just "make" for a list of options. 

  
  Note: In docs/sphinx are two more dirs, wiki2rest and src2rest. These 
        can be used to create reST-formatted documentation from raw sources.
	They depend on a host of external libraries however, so best stay away 
	from them unless you are an Evennia dev. Read the headers of the 
	respective *.py files for instructions. 


-------------------
* Doxygen auto-docs 
-------------------

   In docs/doxygen you can build the developer auto-docs 
   (a fancy searchable index of the entire source tree).
   This makes use of doxygen, a doc generator that parses
   the source tree and creates docs on the fly. 
 
   -  Install doxygen (v1.7+)
  
      Doxygen is available for most platforms from
       http://www.stack.nl/~dimitri/doxygen/ 
      or through your package manager in Linux.

   -  Run   

       > doxygen config.dox
 
      This will create the auto-docs in a folder 'doxygen/html'. 

   -  Start your web browser and point it to 
      
       <evenniadir>/docs/doxygen/html/index.html 

   -  If you prefer a pdf version for printing, use LaTeX by
      activating the relevant section in config.dox. Run the 
      doxygen command again as above and a new folder 'latex' 
      will be created with the latex sources. With the latex
      processing system installed, then run 
      
       > make 
     
      in the newly created folder to create the pdf. Be warned
      however that the pdf docs are >340 pages long!
   
   -  Doxyfile is lavishly documented and allows for plenty of 
      configuration to get the docs to look the way you want. 
      You can also output to other formats suitable for various
      developer environments, Windows help files etc. 
