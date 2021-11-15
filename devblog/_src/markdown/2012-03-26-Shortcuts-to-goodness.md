[![](https://lh4.googleusercontent.com/proxy/QkyxkcgmfR5RuTgXVrmufjqBSJDUNdFKVM50GLVV98Oj7kN0b7IJzWhCK8n1McUG119JfSMFKxCIRW57srOOW0vsPIcnC1D1aHCRJuwvLOydXOMQmkSWg1b9-h92QPchLVw8xYSoWaRB3I8oyHEpPcXEFEO86Vd9hI96fNdasSwU2B4OY5l5zKxmbd2sPIFSH8W6phmRB1lD7NW-sUJk_LQRgjRcl5iPRl9SuaOT3Dgm=s0-d)](http://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/2011_attraction_repulsion_direction_arrows.png/120px-2011_attraction_repulsion_direction_arrows.png)Evennia, being a MUD-design system, needs to take some special considerations with its source code - its sole purpose is after all to be read, understood and extended.  
Python is of course very readable by default and we have worked hard to give extensive comments and documentation. But for a new user looking into the code for the first time, it's still a lot of stuff to take in. Evennia consists of a set of Django-style "applications" interacting and in some cases inheriting from each other so as to avoid code duplication. For a new user to get an overview could therefore mean diving into more layers of code than one would like.  
  
I have now gone through the process of making Evennia's _API_ (Application Programming Interface) "flatter". This has meant exposing some of the most commonly used methods and classes at a higher level and fully documenting exactly what they inherit av every layer one looks at. But I have also added a new module ev.py to the root directory. It  implements "shortcuts" to all the most commonly used parts of the system, forming a very flat API. This means that what used to be  
  
      from src.objects.objects import Object  
  
can now be done as   
  
      from ev import Object  
  
Not only should it be easier to find things (and less boilerplate code to write) but I like that one can also easier explore Evennia interactively this way.  Using a Python interpreter (I recommend ipython) you can just import ev and easily inspect all the important object classes, tab to their properties, helper functions and read their extensive doc strings.  
  
Creating this API, i.e. going through and identifying all the useful entry points a developer will need, was also interesting in that it shows how small the API really is. Most of the ev interface is really various search functions and convenient options to inspect the database in various ways. The MUD-specific parts of the API is really lean, as befits a barebones MUD server/creation system.