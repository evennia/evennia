

Wiki convertion and autodocs
----------------------------

The source/ directory contains Evennia's wiki documentation converted
to ReST form.  This can be built to a html document by installing
python-sphinx (sphinx-doc.org) and running 'make html' from this
directory. The output will appear in under build/ - point your browser
to the index.html file. 

If you want to (re-)build the documentation yourself, wiki2rest/
contains programs for converting Evennia's wiki documentation to ReST
files.  Read the header of wiki2rest.py for setting up the converter. 

The src2rest folder contains a reprecated program for building
documented ReST source code from Evennia's documentation. You can
arguably get as good autodocs using doxygen.
