Auto-generated list of default Evennia commands

Commands in Evennia's default command set
=========================================

*Note: This wiki page is auto-generated from the current status of the
code base and should not be edited manually.*

The commands are ordered after their given help category, which should
usually match a module in ``src/commands/default``. So for example, the
code for a command in the "General" category is most likely to be found
in ``src/commands/default/general.py``.

The default `command set <Commands#Command_Sets.html>`_ currently
contains 86 commands in 6 categories. More information about how
commands work can be found in the `Command
documentation <Commands.html>`_.

Admin
-----

`Link to Python
module <https://code.google.com/p/evennia/source/browse/src/commands/default/admin.py.html>`_

@boot
~~~~~

-  ``key`` = ``@boot``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(boot) or perm(Wizards)``
-  `helpcategory <HelpSystem.html>`_ = ``Admin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @boot     Usage
          @boot[/switches] <player obj> [: reason]    Switches:
          quiet - Silently boot without informing player
          port - boot by port number instead of name or dbref
          
        Boot a player object from the server. If a reason is
        supplied it will be echoed to the user unless /quiet is set.

@boot
~~~~~

-  ``key`` = ``@boot``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(boot) or perm(Wizards)``
-  `helpcategory <HelpSystem.html>`_ = ``Admin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @boot     Usage
          @boot[/switches] <player obj> [: reason]    Switches:
          quiet - Silently boot without informing player
          port - boot by port number instead of name or dbref
          
        Boot a player object from the server. If a reason is
        supplied it will be echoed to the user unless /quiet is set.

@delplayer
~~~~~~~~~~

-  ``key`` = ``@delplayer``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(delplayer) or perm(Immortals)``
-  `helpcategory <HelpSystem.html>`_ = ``Admin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    delplayer - delete player from server    Usage:
          @delplayer[/switch] <name> [: reason]
          
        Switch:
          delobj - also delete the player's currently
                    assigned in-game object.       Completely deletes a user from the server database,
        making their nick and e-mail again available.

@delplayer
~~~~~~~~~~

-  ``key`` = ``@delplayer``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(delplayer) or perm(Immortals)``
-  `helpcategory <HelpSystem.html>`_ = ``Admin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    delplayer - delete player from server    Usage:
          @delplayer[/switch] <name> [: reason]
          
        Switch:
          delobj - also delete the player's currently
                    assigned in-game object.       Completely deletes a user from the server database,
        making their nick and e-mail again available.

@emit
~~~~~

-  ``key`` = ``@emit``
-  ``aliases`` = ``@pemit, @remit``
-  `locks <Locks.html>`_ = ``cmd:perm(emit) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Admin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @emit    Usage:
          @emit[/switches] [<obj>, <obj>, ... =] <message>
          @remit           [<obj>, <obj>, ... =] <message> 
          @pemit           [<obj>, <obj>, ... =] <message>     Switches:
          room : limit emits to rooms only (default)
          players : limit emits to players only 
          contents : send to the contents of matched objects too
          
        Emits a message to the selected objects or to
        your immediate surroundings. If the object is a room,
        send to its contents. @remit and @pemit are just 
        limited forms of @emit, for sending to rooms and 
        to players respectively.

@perm
~~~~~

-  ``key`` = ``@perm``
-  ``aliases`` = ``@setperm``
-  `locks <Locks.html>`_ = ``cmd:perm(perm) or perm(Immortals)``
-  `helpcategory <HelpSystem.html>`_ = ``Admin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @perm - set permissions    Usage:
          @perm[/switch] <object> [= <permission>[,<permission>,...]]
          @perm[/switch] *<player> [= <permission>[,<permission>,...]]
          
        Switches:
          del : delete the given permission from <object> or <player>.
          player : set permission on a player (same as adding * to name)    This command sets/clears individual permission strings on an object 
        or player. If no permission is given, list all permissions on <object>.

@userpassword
~~~~~~~~~~~~~

-  ``key`` = ``@userpassword``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(newpassword) or perm(Wizards)``
-  `helpcategory <HelpSystem.html>`_ = ``Admin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @setpassword    Usage:
          @userpassword <user obj> = <new password>    Set a player's password.

@userpassword
~~~~~~~~~~~~~

-  ``key`` = ``@userpassword``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(newpassword) or perm(Wizards)``
-  `helpcategory <HelpSystem.html>`_ = ``Admin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @setpassword    Usage:
          @userpassword <user obj> = <new password>    Set a player's password.

@wall
~~~~~

-  ``key`` = ``@wall``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(wall) or perm(Wizards)``
-  `helpcategory <HelpSystem.html>`_ = ``Admin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @wall    Usage:
          @wall <message>
          
        Announces a message to all connected players.

Building
--------

`Link to Python
module <https://code.google.com/p/evennia/source/browse/src/commands/default/building.py.html>`_

@alias
~~~~~~

-  ``key`` = ``@alias``
-  ``aliases`` = ``@setobjalias``
-  `locks <Locks.html>`_ = ``cmd:perm(setobjalias) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    Adding permanent aliases    Usage:
          @alias <obj> [= [alias[,alias,alias,...]]]    Assigns aliases to an object so it can be referenced by more 
        than one name. Assign empty to remove all aliases from object.
        Observe that this is not the same thing as aliases 
        created with the 'alias' command! Aliases set with @alias are 
        changing the object in question, making those aliases usable 
        by everyone.

@batchcode
~~~~~~~~~~

-  ``key`` = ``@batchcode``
-  ``aliases`` = ``@batchcodes``
-  `locks <Locks.html>`_ = ``cmd:perm(batchcommands) or superuser()``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    Build from batch-code file    Usage:
         @batchcode[/interactive] <python path to file>    Switch:
           interactive - this mode will offer more control when
                         executing the batch file, like stepping,
                         skipping, reloading etc. 
           debug - auto-delete all objects that has been marked as
                   deletable in the script file (see example files for
                   syntax). This is useful so as to to not leave multiple
                   object copies behind when testing out the script.    Runs batches of commands from a batch-code text file (*.py).

@batchcommands
~~~~~~~~~~~~~~

-  ``key`` = ``@batchcommands``
-  ``aliases`` = ``@batchcommand, @batchcmd``
-  `locks <Locks.html>`_ = ``cmd:perm(batchcommands) or superuser()``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    Build from batch-command file    Usage:
         @batchcommands[/interactive] <python.path.to.file>    Switch:
           interactive - this mode will offer more control when
                         executing the batch file, like stepping,
                         skipping, reloading etc.     Runs batches of commands from a batch-cmd text file (*.ev).

@cmdsets
~~~~~~~~

-  ``key`` = ``@cmdsets``
-  ``aliases`` = ``@listcmsets``
-  `locks <Locks.html>`_ = ``cmd:perm(listcmdsets) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    list command sets on an object    Usage:
          @cmdsets [obj]    This displays all cmdsets assigned
        to a user. Defaults to yourself.

@copy
~~~~~

-  ``key`` = ``@copy``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(copy) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @copy - copy objects
        
        Usage:
          @copy[/reset] <original obj> [= new_name][;alias;alias..][:new_location] [,new_name2 ...]     switch:
          reset - make a 'clean' copy off the object, thus
                  removing any changes that might have been made to the original
                  since it was first created.     Create one or more copies of an object. If you don't supply any targets, one exact copy
        of the original object will be created with the name *_copy.

@cpattr
~~~~~~~

-  ``key`` = ``@cpattr``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(cpattr) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @cpattr - copy attributes    Usage:    
          @cpattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
          @cpattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
          @cpattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
          @cpattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]    Switches:
          move - delete the attribute from the source object after copying.     Example:
          @cpattr coolness = Anna/chillout, Anna/nicety, Tom/nicety
          ->
          copies the coolness attribute (defined on yourself), to attributes
          on Anna and Tom.     Copy the attribute one object to one or more attributes on another object. If
        you don't supply a source object, yourself is used.

@create
~~~~~~~

-  ``key`` = ``@create``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(create) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @create - create new objects    Usage:
          @create[/drop] objname[;alias;alias...][:typeclass], objname...    switch:
           drop - automatically drop the new object into your current location (this is not echoed)
                  this also sets the new object's home to the current location rather than to you.    Creates one or more new objects. If typeclass is given, the object
        is created as a child of this typeclass. The typeclass script is
        assumed to be located under game/gamesrc/types and any further
        directory structure is given in Python notation. So if you have a
        correct typeclass object defined in
        game/gamesrc/types/examples/red_button.py, you could create a new
        object of this type like this:        @create button;red : examples.red_button.RedButton

@debug
~~~~~~

-  ``key`` = ``@debug``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(debug) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    Debug game entities    Usage:
          @debug[/switch] <path to code>    Switches:
          obj - debug an object
          script - debug a script    Examples:
          @debug/script game.gamesrc.scripts.myscript.MyScript
          @debug/script myscript.MyScript
          @debug/obj examples.red_button.RedButton    This command helps when debugging the codes of objects and scripts.
        It creates the given object and runs tests on its hooks.

@desc
~~~~~

-  ``key`` = ``@desc``
-  ``aliases`` = ``@describe``
-  `locks <Locks.html>`_ = ``cmd:perm(desc) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @desc - describe an object or room    Usage:
          @desc [<obj> =] >description>    Setts the "desc" attribute on an 
        object. If an object is not given,
        describe the current room.

@destroy
~~~~~~~~

-  ``key`` = ``@destroy``
-  ``aliases`` = ``@delete, @del``
-  `locks <Locks.html>`_ = ``cmd:perm(destroy) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @destroy - remove objects from the game
        
        Usage: 
           @destroy[/switches] [obj, obj2, obj3, [dbref-dbref], ...]
                  
        switches:
           override - The @destroy command will usually avoid accidentally destroying
                      player objects. This switch overrides this safety.            
        examples:
           @destroy house, roof, door, 44-78
           @destroy 5-10, flower, 45    Destroys one or many objects. If dbrefs are used, a range to delete can be
        given, e.g. 4-10. Also the end points will be deleted.

@dig
~~~~

-  ``key`` = ``@dig``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(dig) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @dig - build and connect new rooms to the current one    Usage: 
          @dig[/switches] roomname[;alias;alias...][:typeclass] 
                [= exit_to_there[;alias][:typeclass]] 
                   [, exit_to_here[;alias][:typeclass]]     Switches:
           tel or teleport - move yourself to the new room    Examples:
           @dig kitchen = north;n, south;s
           @dig house:myrooms.MyHouseTypeclass
           @dig sheer cliff;cliff;sheer = climb up, climb down    This command is a convenient way to build rooms quickly; it creates the new room and you can optionally
        set up exits back and forth between your current room and the new one. You can add as many aliases as you
        like to the name of the room and the exits in question; an example would be 'north;no;n'.

@examine
~~~~~~~~

-  ``key`` = ``@examine``
-  ``aliases`` = ``@ex, ex, exam, examine``
-  `locks <Locks.html>`_ = ``cmd:perm(examine) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    examine - detailed info on objects    Usage: 
          examine [<object>[/attrname]]
          examine [*<player>[/attrname]]    Switch:
          player - examine a Player (same as adding *)
          raw - don't parse escape codes for data.     The examine command shows detailed game info about an
        object and optionally a specific attribute on it. 
        If object is not specified, the current location is examined.     Append a * before the search string to examine a player.

@find
~~~~~

-  ``key`` = ``@find``
-  ``aliases`` = ``find, @search, search, @locate, locate``
-  `locks <Locks.html>`_ = ``cmd:perm(find) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    find objects    Usage:
          @find[/switches] <name or dbref or *player> [= dbrefmin[-dbrefmax]]    Switches:
          room - only look for rooms (location=None)
          exit - only look for exits (destination!=None)
          char - only look for characters (BASE_CHARACTER_TYPECLASS)    Searches the database for an object of a particular name or dbref.
        Use *playername to search for a player. The switches allows for
        limiting object matches to certain game entities. Dbrefmin and dbrefmax 
        limits matches to within the given dbrefs, or above/below if only one is given.

@help
~~~~~

-  ``key`` = ``@help``
-  ``aliases`` = ``@sethelp``
-  `locks <Locks.html>`_ = ``cmd:perm(PlayerHelpers)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @help - edit the help database    Usage:
          @help[/switches] <topic>[,category[,locks]] = <text>    Switches:
          add    - add or replace a new topic with text.
          append - add text to the end of topic with a newline between.
          merge  - As append, but don't add a newline between the old
                   text and the appended text. 
          delete - remove help topic.
          force  - (used with add) create help topic also if the topic
                   already exists.     Examples:
          @sethelp/add throw = This throws something at ...
          @sethelp/append pickpocketing,Thievery,is_thief, is_staff) = This steals ...
          @sethelp/append pickpocketing, ,is_thief, is_staff) = This steals ...

@home
~~~~~

-  ``key`` = ``@home``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(@home) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @home - control an object's home location    Usage:
          @home <obj> [= home_location]    The "home" location is a "safety" location for objects; they
        will be moved there if their current location ceases to exist. All
        objects should always have a home location for this reason. 
        It is also a convenient target of the "home" command.     If no location is given, just view the object's home location.

@link
~~~~~

-  ``key`` = ``@link``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(link) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @link - connect objects    Usage:
          @link[/switches] <object> = <target>
          @link[/switches] <object> = 
          @link[/switches] <object> 
         
        Switch:
          twoway - connect two exits. For this to work, BOTH <object>
                   and <target> must be exit objects.     If <object> is an exit, set its destination to <target>. Two-way operation
        instead sets the destination to the *locations* of the respective given
        arguments. 
        The second form (a lone =) sets the destination to None (same as the @unlink command)
        and the third form (without =) just shows the currently set destination.

@lock
~~~~~

-  ``key`` = ``@lock``
-  ``aliases`` = ``@locks, lock, locks``
-  `locks <Locks.html>`_ = ``cmd: perm(@locks) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    lock - assign a lock definition to an object    Usage:
          @lock <object>[ = <lockstring>]
          or 
          @lock[/switch] object/<access_type>
          
        Switch:
          del - delete given access type
          view - view lock associated with given access type (default)
        
        If no lockstring is given, shows all locks on
        object.     Lockstring is on the form
           'access_type:[NOT] func1(args)[ AND|OR][ NOT] func2(args) ...]
        Where func1, func2 ... valid lockfuncs with or without arguments. 
        Separator expressions need not be capitalized.    For example: 
           'get: id(25) or perm(Wizards)'
        The 'get' access_type is checked by the get command and will
        an object locked with this string will only be possible to 
        pick up by Wizards or by object with id 25.
        
        You can add several access_types after oneanother by separating
        them by ';', i.e:
           'get:id(25);delete:perm(Builders)'

@mvattr
~~~~~~~

-  ``key`` = ``@mvattr``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(mvattr) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @mvattr - move attributes    Usage:    
          @mvattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
          @mvattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
          @mvattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
          @mvattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]    Switches:
          copy - Don't delete the original after moving.     Move an attribute from one object to one or more attributes on another object. If
        you don't supply a source object, yourself is used.

@name
~~~~~

-  ``key`` = ``@name``
-  ``aliases`` = ``@rename``
-  `locks <Locks.html>`_ = ``cmd:perm(rename) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    cname - change the name and/or aliases of an object
        
        Usage: 
          @name obj = name;alias1;alias2     
        
        Rename an object to something new.

@open
~~~~~

-  ``key`` = ``@open``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(open) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @open - create new exit
        
        Usage:
          @open <new exit>[;alias;alias..][:typeclass] [,<return exit>[;alias;..][:typeclass]]] = <destination>     Handles the creation of exits. If a destination is given, the exit
        will point there. The <return exit> argument sets up an exit at the
        destination leading back to the current room. Destination name
        can be given both as a #dbref and a name, if that name is globally
        unique.

@script
~~~~~~~

-  ``key`` = ``@script``
-  ``aliases`` = ``@addscript``
-  `locks <Locks.html>`_ = ``cmd:perm(script) or perm(Wizards)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    attach scripts    Usage:
          @script[/switch] <obj> [= <script.path or scriptkey>]
        
        Switches:
          start - start all non-running scripts on object, or a given script only
          stop - stop all scripts on objects, or a given script only    If no script path/key is given, lists all scripts active on the given
        object. 
        Script path can be given from the base location for scripts as given in
        settings. If adding a new script, it will be started automatically (no /start
        switch is needed). Using the /start or /stop switches on an object without 
        specifying a script key/path will start/stop ALL scripts on the object.

@set
~~~~

-  ``key`` = ``@set``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(set) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @set - set attributes    Usage:
          @set <obj>/<attr> = <value>
          @set <obj>/<attr> =  
          @set <obj>/<attr>
       
        Sets attributes on objects. The second form clears
        a previously set attribute while the last form
        inspects the current value of the attribute 
        (if any). You can also set lists [...] and dicts ...
        on attributes with @set (but not nested combinations). Also
        note that such lists/dicts will always hold strings (never numbers).
        Use @py if you need to set arbitrary lists and dicts.

@tel
~~~~

-  ``key`` = ``@tel``
-  ``aliases`` = ``@teleport``
-  `locks <Locks.html>`_ = ``cmd:perm(teleport) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    teleport    Usage:
          @tel/switch [<object> =] <location>    Switches:
          quiet  - don't inform the source and target
                   locations about the move. 
                  
        Teleports an object somewhere. If no object is
        given we are teleporting ourselves.

@tunnel
~~~~~~~

-  ``key`` = ``@tunnel``
-  ``aliases`` = ``@tun``
-  `locks <Locks.html>`_ = ``cmd: perm(tunnel) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    dig in often-used directions    Usage: 
          @tunnel[/switch] <direction> [= roomname[;alias;alias;...][:typeclass]]    Switches:
          oneway - do not create an exit back to the current location
          tel - teleport to the newly created room     Example:
          @tunnel n
          @tunnel n = house;mike's place;green building
        
        This is a simple way to build using pre-defined directions: 
         wn,ne,e,se,s,sw,w,nwn (north, northeast etc)
         wu,dn (up and down) 
         wi,on (in and out)
        The full names (north, in, southwest, etc) will always be put as
        main name for the exit, using the abbreviation as an alias (so an
        exit will always be able to be used with both "north" as well as
        "n" for example). Opposite directions will automatically be
        created back from the new room unless the /oneway switch is given.
        For more flexibility and power in creating rooms, use @dig.

@typeclass
~~~~~~~~~~

-  ``key`` = ``@typeclass``
-  ``aliases`` = ``@type, @parent``
-  `locks <Locks.html>`_ = ``cmd:perm(typeclass) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @typeclass - set object typeclass     Usage:     
          @typclass[/switch] <object> [= <typeclass path>]
          @type           ''
          @parent         ''    Switch:
          reset - clean out *all* the attributes on the object - 
                  basically making this a new clean object. 
          force - change to the typeclass also if the object
                  already has a typeclass of the same name.      
        Example:
          @type button = examples.red_button.RedButton
          
        Sets an object's typeclass. The typeclass must be identified
        by its location using python dot-notation pointing to the correct
        module and class. If no typeclass is given (or a wrong typeclass
        is given), the object will be set to the default typeclass.
        The location of the typeclass module is searched from
        the default typeclass directory, as defined in the server settings.

@unlink
~~~~~~~

-  ``key`` = ``@unlink``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(unlink) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @unlink - unconnect objects    Usage:
          @unlink <Object>    Unlinks an object, for example an exit, disconnecting
        it from whatever it was connected to.

@wipe
~~~~~

-  ``key`` = ``@wipe``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(wipe) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``Building``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @wipe - clears attributes    Usage:
          @wipe <object>[/attribute[/attribute...]]    Example:
          @wipe box 
          @wipe box/colour    Wipes all of an object's attributes, or optionally only those
        matching the given attribute-wildcard search string.

Comms
-----

`Link to Python
module <https://code.google.com/p/evennia/source/browse/src/commands/default/comms.py.html>`_

@cboot
~~~~~~

-  ``key`` = ``@cboot``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd: not pperm(channel_banned)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @cboot    Usage:
           @cboot[/quiet] <channel> = <player> [:reason]    Switches:
           quiet - don't notify the channel    Kicks a player or object from a channel you control.

@ccreate
~~~~~~~~

-  ``key`` = ``@ccreate``
-  ``aliases`` = ``channelcreate``
-  `locks <Locks.html>`_ = ``cmd:not pperm(channel_banned)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @ccreate
        channelcreate 
        Usage:
         @ccreate <new channel>[;alias;alias...] = description    Creates a new channel owned by you.

@cdesc
~~~~~~

-  ``key`` = ``@cdesc``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:not pperm(channel_banned)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @cdesc - set channel description    Usage:
          @cdesc <channel> = <description>    Changes the description of the channel as shown in
        channel lists.

@cdestroy
~~~~~~~~~

-  ``key`` = ``@cdestroy``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd: not pperm(channel_banned)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @cdestroy    Usage:
          @cdestroy <channel>    Destroys a channel that you control.

@cemit
~~~~~~

-  ``key`` = ``@cemit``
-  ``aliases`` = ``@cmsg``
-  `locks <Locks.html>`_ = ``cmd: not pperm(channel_banned)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @cemit - send a message to channel    Usage:
          @cemit[/switches] <channel> = <message>    Switches:
          noheader - don't show the [channel] header before the message
          sendername - attach the sender's name before the message
          quiet - don't echo the message back to sender    Allows the user to broadcast a message over a channel as long as
        they control it. It does not show the user's name unless they
        provide the /sendername switch.

@channels
~~~~~~~~~

-  ``key`` = ``@channels``
-  ``aliases`` =
   ``@clist, channels, comlist, chanlist, channellist, all channels``
-  `locks <Locks.html>`_ = ``cmd: not pperm(channel_banned)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @clist    Usage:
          @channels
          @clist
          comlist    Lists all channels available to you, wether you listen to them or not. 
        Use 'comlist" to only view your current channel subscriptions.

@cset
~~~~~

-  ``key`` = ``@cset``
-  ``aliases`` = ``@cclock``
-  `locks <Locks.html>`_ = ``cmd:not pperm(channel_banned)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @cset - changes channel access restrictions
        
        Usage:
          @cset <channel> [= <lockstring>]    Changes the lock access restrictions of a channel. If no
        lockstring was given, view the current lock definitions.

@cwho
~~~~~

-  ``key`` = ``@cwho``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd: not pperm(channel_banned)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @cwho
        
        Usage: 
          @cwho <channel>    List who is connected to a given channel you have access to.

@imc2chan
~~~~~~~~~

-  ``key`` = ``@imc2chan``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ =
   ``cmd:serversetting(IMC2_ENABLED) and pperm(Immortals)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    imc2chan - link an evennia channel to imc2    Usage:
          @imc2chan[/switches] <evennia_channel> = <imc2_channel>    Switches:
          /disconnect - this clear the imc2 connection to the channel.
          /remove     -                " 
          /list       - show all imc2<->evennia mappings    Example:
          @imc2chan myimcchan = ievennia
          
        Connect an existing evennia channel to a channel on an IMC2
        network. The network contact information is defined in settings and
        should already be accessed at this point. Use @imcchanlist to see
        available IMC channels.

@imcinfo
~~~~~~~~

-  ``key`` = ``@imcinfo``
-  ``aliases`` = ``@imcchanlist, @imclist, @imcwhois``
-  `locks <Locks.html>`_ =
   ``cmd: serversetting(IMC2_ENABLED) and pperm(Wizards)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    imcinfo - package of imc info commands    Usage:
          @imcinfo[/switches]
          @imcchanlist - list imc2 channels
          @imclist -     list connected muds 
          @imcwhois <playername> - whois info about a remote player    Switches for @imcinfo:
          channels - as @imcchanlist (default)
          games or muds - as @imclist 
          whois - as @imcwhois (requires an additional argument)
          update - force an update of all lists
         
        Shows lists of games or channels on the IMC2 network.

@irc2chan
~~~~~~~~~

-  ``key`` = ``@irc2chan``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ =
   ``cmd:serversetting(IRC_ENABLED) and pperm(Immortals)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @irc2chan - link evennia channel to an IRC channel    Usage:
          @irc2chan[/switches] <evennia_channel> = <ircnetwork> <port> <#irchannel> <botname>    Switches:
          /disconnect - this will delete the bot and remove the irc connection to the channel.
          /remove     -                                 " 
          /list       - show all irc<->evennia mappings    Example:
          @irc2chan myircchan = irc.dalnet.net 6667 myevennia-channel evennia-bot    This creates an IRC bot that connects to a given IRC network and channel. It will 
        relay everything said in the evennia channel to the IRC channel and vice versa. The 
        bot will automatically connect at server start, so this comman need only be given once. 
        The /disconnect switch will permanently delete the bot. To only temporarily deactivate it, 
        use the @services command instead.

addcom
~~~~~~

-  ``key`` = ``addcom``
-  ``aliases`` = ``aliaschan, chanalias``
-  `locks <Locks.html>`_ = ``cmd:not pperm(channel_banned)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    addcom - subscribe to a channel with optional alias    Usage:
           addcom [alias=] <channel>
           
        Joins a given channel. If alias is given, this will allow you to
        refer to the channel by this alias rather than the full channel
        name. Subsequent calls of this command can be used to add multiple
        aliases to an already joined channel.

allcom
~~~~~~

-  ``key`` = ``allcom``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd: not pperm(channel_banned)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    allcom - operate on all channels    Usage:    
          allcom [on | off | who | destroy]          Allows the user to universally turn off or on all channels they are on,
        as well as perform a 'who' for all channels they are on. Destroy deletes
        all channels that you control.    Without argument, works like comlist.

delcom
~~~~~~

-  ``key`` = ``delcom``
-  ``aliases`` = ``delaliaschan, delchanalias``
-  `locks <Locks.html>`_ = ``cmd:not perm(channel_banned)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    delcom - unsubscribe from channel or remove channel alias    Usage:
           delcom <alias or channel>    If the full channel name is given, unsubscribe from the
        channel. If an alias is given, remove the alias but don't
        unsubscribe.

imctell
~~~~~~~

-  ``key`` = ``imctell``
-  ``aliases`` = ``imcpage, imc2tell, imc2page``
-  `locks <Locks.html>`_ = ``cmd: serversetting(IMC2_ENABLED)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    imctell - send a page to a remote IMC player    Usage: 
          imctell User@MUD = <msg> 
          imcpage      "     Sends a page to a user on a remote MUD, connected
        over IMC2.

page
~~~~

-  ``key`` = ``page``
-  ``aliases`` = ``tell``
-  `locks <Locks.html>`_ = ``cmd:not pperm(page_banned)``
-  `helpcategory <HelpSystem.html>`_ = ``Comms``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    page - send private message    Usage:
          page[/switches] [<player>,<player>,... = <message>]
          tell        ''
          page <number>    Switch:
          last - shows who you last messaged
          list - show your last <number> of tells/pages (default)
          
        Send a message to target user (if online). If no
        argument is given, you will get a list of your latest messages.

General
-------

`Link to Python
module <https://code.google.com/p/evennia/source/browse/src/commands/default/general.py.html>`_

@encoding
~~~~~~~~~

-  ``key`` = ``@encoding``
-  ``aliases`` = ``@encode``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    encoding - set a custom text encoding    Usage: 
          @encoding/switches [<encoding>]    Switches:
          clear - clear your custom encoding           
        This sets the text encoding for communicating with Evennia. This is mostly an issue only if 
        you want to use non-ASCII characters (i.e. letters/symbols not found in English). If you see
        that your characters look strange (or you get encoding errors), you should use this command
        to set the server encoding to be the same used in your client program. 
        
        Common encodings are utf-8 (default), latin-1, ISO-8859-1 etc.
        
        If you don't submit an encoding, the current encoding will be displayed instead.

@ic
~~~

-  ``key`` = ``@ic``
-  ``aliases`` = ``@puppet``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    Switch control to an object
        
        Usage:
          @ic <character>
          
        Go in-character (IC) as a given Character.     This will attempt to "become" a different object assuming you have
        the right to do so.  You cannot become an object that is already
        controlled by another player. In principle <character> can be
        any in-game object as long as you have access right to puppet it.

@ooc
~~~~

-  ``key`` = ``@ooc``
-  ``aliases`` = ``@unpuppet``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @ooc - go ooc
        
        Usage:
          @ooc
          
        Go out-of-character (OOC).    This will leave your current character and put you in a incorporeal OOC state.

@password
~~~~~~~~~

-  ``key`` = ``@password``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @password - set your password    Usage:
          @password <old password> = <new password>    Changes your password. Make sure to pick a safe one.

@quit
~~~~~

-  ``key`` = ``@quit``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    quit    Usage:
          @quit     Gracefully disconnect from the game.

access
~~~~~~

-  ``key`` = ``access``
-  ``aliases`` = ``groups, hierarchy``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    access - show access groups    Usage:
          access    This command shows you the permission hierarchy and 
        which permission groups you are a member of.

drop
~~~~

-  ``key`` = ``drop``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    drop    Usage:
          drop <obj>
          
        Lets you drop an object from your inventory into the 
        location you are currently in.

get
~~~

-  ``key`` = ``get``
-  ``aliases`` = ``grab``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    get    Usage:
          get <obj>
          
        Picks up an object from your location and puts it in
        your inventory.

help
~~~~

-  ``key`` = ``help``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    The main help command    Usage:
          help <topic or command>
          help list
          help all    This will search for help on commands and other
        topics related to the game.

help
~~~~

-  ``key`` = ``help``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    The main help command    Usage:
          help <topic or command>
          help list
          help all    This will search for help on commands and other
        topics related to the game.

home
~~~~

-  ``key`` = ``home``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(home) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    home    Usage:
          home     Teleports the player to their home.

inventory
~~~~~~~~~

-  ``key`` = ``inventory``
-  ``aliases`` = ``inv, i``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    inventory    Usage:
          inventory
          inv
          
        Shows a player's inventory.

look
~~~~

-  ``key`` = ``look``
-  ``aliases`` = ``l, ls``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    look    Usage:
          look
          look <obj> 
          look *<player>    Observes your location or objects in your vicinity.

look
~~~~

-  ``key`` = ``look``
-  ``aliases`` = ``l, ls``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    ooc look    Usage:
          look    This is an OOC version of the look command. Since a
        Player doesn't have an in-game existence, there is no
        concept of location or "self". If we are controlling 
        a character, pass control over to normal look.

nick
~~~~

-  ``key`` = ``nick``
-  ``aliases`` = ``nickname, nicks, @nick, alias``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    Define a personal alias/nick    Usage:
          nick[/switches] <nickname> = [<string>]
          alias             ''    Switches:      
          object   - alias an object
          player   - alias a player 
          clearall - clear all your aliases
          list     - show all defined aliases 
          
        If no switch is given, a command alias is created, used
        to replace strings before sending the command. Give an empty
        right-hand side to clear the nick
          
        Creates a personal nick for some in-game object or
        string. When you enter that string, it will be replaced
        with the alternate string. The switches dictate in what
        situations the nick is checked and substituted. If string
        is None, the alias (if it exists) will be cleared.
        Obs - no objects are actually changed with this command,
        if you want to change the inherent aliases of an object,
        use the @alias command instead.

pose
~~~~

-  ``key`` = ``pose``
-  ``aliases`` = ``:, emote``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    pose - strike a pose    Usage:
          pose <pose text>
          pose's <pose text>    Example:
          pose is standing by the wall, smiling.
           -> others will see:
         Tom is standing by the wall, smiling.        Describe an script being taken. The pose text will
        automatically begin with your name.

say
~~~

-  ``key`` = ``say``
-  ``aliases`` = ``"``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    say    Usage:
          say <message>
          
        Talk to those in your current location.

who
~~~

-  ``key`` = ``who``
-  ``aliases`` = ``doing``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``General``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    who    Usage:
          who 
          doing     Shows who is currently online. Doing is an alias that limits info
        also for those with all permissions.

System
------

`Link to Python
module <https://code.google.com/p/evennia/source/browse/src/commands/default/system.py.html>`_

@objects
~~~~~~~~

-  ``key`` = ``@objects``
-  ``aliases`` = ``@listobjects, @listobjs, @stats, @db``
-  `locks <Locks.html>`_ = ``cmd:perm(listobjects) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``System``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    Give a summary of object types in database    Usage:
          @objects [<nr>]    Gives statictics on objects in database as well as 
        a list of <nr> latest objects in database. If not 
        given, <nr> defaults to 10.

@ps
~~~

-  ``key`` = ``@ps``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(ps) or perm(Builders)``
-  `helpcategory <HelpSystem.html>`_ = ``System``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    list processes
        
        Usage
          @ps     Shows the process/event table.

@py
~~~

-  ``key`` = ``@py``
-  ``aliases`` = ``!``
-  `locks <Locks.html>`_ = ``cmd:perm(py) or perm(Immortals)``
-  `helpcategory <HelpSystem.html>`_ = ``System``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    Execute a snippet of python code     Usage:
          @py <cmd>    Separate multiple commands by ';'.  A few variables are made
        available for convenience in order to offer access to the system
        (you can import more at execution time).    Available variables in @py environment: 
          self, me                   : caller
          here                       : caller.location
          obj                        : dummy obj instance
          script                     : dummy script instance
          config                     : dummy conf instance                    
          ObjectDB                   : ObjectDB class
          ScriptDB                   : ScriptDB class
          ServerConfig               : ServerConfig class
          inherits_from(obj, parent) : check object inheritance    rNote: In the wrong hands this command is a severe security risk.
        It should only be accessible by trusted server admins/superusers.n

@reload
~~~~~~~

-  ``key`` = ``@reload``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(reload) or perm(Immortals)``
-  `helpcategory <HelpSystem.html>`_ = ``System``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    Reload the system    Usage:
          @reload    This restarts the server. The Portal is not
        affected. Non-persistent scripts will survive a @reload (use
        @reset to purge) and at_reload() hooks will be called.

@reset
~~~~~~

-  ``key`` = ``@reset``
-  ``aliases`` = ``@reboot``
-  `locks <Locks.html>`_ = ``cmd:perm(reload) or perm(Immortals)``
-  `helpcategory <HelpSystem.html>`_ = ``System``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    Reset and reboot the system    Usage:
          @reset    A cold reboot. This works like a mixture of @reload and @shutdown,
        - all shutdown hooks will be called and non-persistent scrips will
        be purged. But the Portal will not be affected and the server will
        automatically restart again.

@scripts
~~~~~~~~

-  ``key`` = ``@scripts``
-  ``aliases`` = ``@listscripts``
-  `locks <Locks.html>`_ = ``cmd:perm(listscripts) or perm(Wizards)``
-  `helpcategory <HelpSystem.html>`_ = ``System``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    Operate on scripts.    Usage:
          @scripts[/switches] [<obj or scriptid>]
          
        Switches:
          stop - stops an existing script
          kill - kills a script - without running its cleanup hooks
          validate - run a validation on the script(s)    If no switches are given, this command just views all active
        scripts. The argument can be either an object, at which point it
        will be searched for all scripts defined on it, or an script name
        or dbref. For using the /stop switch, a unique script dbref is
        required since whole classes of scripts often have the same name.

@serverload
~~~~~~~~~~~

-  ``key`` = ``@serverload``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(list) or perm(Immortals)``
-  `helpcategory <HelpSystem.html>`_ = ``System``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    server load statistics    Usage:
           @serverload    Show server load statistics in a table.

@service
~~~~~~~~

-  ``key`` = ``@service``
-  ``aliases`` = ``@services``
-  `locks <Locks.html>`_ = ``cmd:perm(service) or perm(Immortals)``
-  `helpcategory <HelpSystem.html>`_ = ``System``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @service - manage services    Usage:
          @service[/switch] <service>    Switches:
          list   - shows all available services (default)
          start  - activates a service
          stop   - stops a service
          
        Service management system. Allows for the listing,
        starting, and stopping of services. If no switches
        are given, services will be listed.

@shutdown
~~~~~~~~~

-  ``key`` = ``@shutdown``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(shutdown) or perm(Immortals)``
-  `helpcategory <HelpSystem.html>`_ = ``System``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @shutdown    Usage:
          @shutdown [announcement]    Gracefully shut down both Server and Portal.

@time
~~~~~

-  ``key`` = ``@time``
-  ``aliases`` = ``@uptime``
-  `locks <Locks.html>`_ = ``cmd:perm(time) or perm(Players)``
-  `helpcategory <HelpSystem.html>`_ = ``System``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @time    Usage:
          @time 
        
        Server local time.

@version
~~~~~~~~

-  ``key`` = ``@version``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``<No access>``
-  `helpcategory <HelpSystem.html>`_ = ``System``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    @version - game version    Usage:
          @version    Display the game version info.

Unloggedin
----------

`Link to Python
module <https://code.google.com/p/evennia/source/browse/src/commands/default/unloggedin.py.html>`_

**unloggedin*look*command
~~~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``__unloggedin_look_command``
-  ``aliases`` = ``look, l``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``Unloggedin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    This is an unconnected version of the look command for simplicity.     This is called by the server and kicks everything in gear. 
        All it does is display the connect screen.

connect
~~~~~~~

-  ``key`` = ``connect``
-  ``aliases`` = ``conn, con, co``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``Unloggedin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    Connect to the game.    Usage (at login screen): 
          connect <email> <password>
          
        Use the create command to first create an account before logging in.

create
~~~~~~

-  ``key`` = ``create``
-  ``aliases`` = ``cre, cr``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``Unloggedin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    Create a new account.    Usage (at login screen):
          create "playername" <email> <password>    This creates a new player account.

help
~~~~

-  ``key`` = ``help``
-  ``aliases`` = ``h, ?``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``Unloggedin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    This is an unconnected version of the help command,
        for simplicity. It shows a pane or info.

quit
~~~~

-  ``key`` = ``quit``
-  ``aliases`` = ``q, qu``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `helpcategory <HelpSystem.html>`_ = ``Unloggedin``
-  `Auto-help <HelpSystem#Auto-help%3C/i%3Esystem.html>`_
   (``__doc__ string``) =

::

    We maintain a different version of the quit command
        here for unconnected players for the sake of simplicity. The logged in
        version is a bit more complicated.

