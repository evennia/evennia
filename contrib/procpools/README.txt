
ProcPools
---------

This contrib defines a process pool subsystem for Evennia.

A process pool handles a range of separately running processes that
can accept information from the main Evennia process. The pool dynamically
grows and shrinks depending on the need (and will queue requests if there
are no free slots available).

The main use of this is to launch long-running, possibly blocking code
in a way that will not freeze up the rest of the server. So you could 
execute time.sleep(10) on the process pool without anyone else on the 
server noticing anything. 

This folder has the following contents: 

ampoule/ - this is a separate library managing the process pool. You 
           should not need to touch this.

Python Procpool
---------------
python_procpool.py - this implements a way to execute arbitrary python
           code on the procpool. Import run_async() from this
           module in order to use this functionality in-code
           (this is a replacement to the in-process run_async
           found in src.utils.utils).
python_procpool_plugin.py - this is a plugin module for the python
           procpool, to start and add it to the server. Adding it 
           is a single line in your settings file - see the header
           of the file for more info. 



Adding other Procpools
----------------------
To add other types of procpools (such as for executing other remote languages
           than Python), you can pretty much mimic the layout of python_procpool.py
           and python_procpool_plugin.py.
