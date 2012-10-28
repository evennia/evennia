Commands in Evennia's default command set
=========================================

*Note: This wiki page is auto-generated from the current status of the
code base and should not be edited manually.*

The commands are ordered after their given help category, which should
usually match a module in ``src/commands/default``. So for example, the
code for a command in the "General" category is most likely to be found
in ``src/commands/default/general.py``.

The commands that make up the default [Commands#Command\_Sets command
set] are divided into three sub-sets after which objects they are
defined on.

-  An *OOC Command* is a command in the OOCCmdset, available only on
   Players, not on Objects/Characters. Since Players control Characters,
   the OOC and default cmdset are normally merged together and the
   difference is not noticeable. Use e.g. the ``@ooc`` command to
   disconnect from the current character and see only the OOC cmdset.
   Same-keyed command on the Character has higher priority than its OOC
   equivalent, allowing to overload the OOC commands on a per-Character
   basis.
-  An *Unloggedin Command* sits in UnloggedinCmdset. They are specific
   to the login screen, before the session (User) has authenticated.
-  All other commands are *On-Character* commands, commands defined in
   DefaultCmdset and available in the game.

The full set of available commands (all three sub-sets above) currently
contains 86 commands in 6 categories. More information about how
commands work can be found in the `Command <Commands.html>`_
documentation.

Admin
-----

`Link to Python
module <https://code.google.com/p/evennia/source/browse/src/commands/default/admin.py>`_

@ban
~~~~

-  ``key`` = ``@ban``
-  ``aliases`` = ``@bans``
-  `locks <Locks.html>`_ = ``cmd:perm(ban) or perm(Immortals)``
-  `help\_category <HelpSystem.html>`_ = ``Admin``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        ban a player from the server

        Usage:
          @ban [<name or ip> [: reason]]

        Without any arguments, shows numbered list of active bans.

        This command bans a user from accessing the game. Supply an
        optional reason to be able to later remember why the ban was put in
        place

        It is often to
        prefer over deleting a player with @delplayer. If banned by name,
        that player account can no longer be logged into.

        IP (Internet Protocol) address banning allows to block all access
        from a specific address or subnet. Use the asterisk (*) as a
        wildcard.

        Examples:
          @ban thomas             - ban account 'thomas'
          @ban/ip 134.233.2.111   - ban specific ip address
          @ban/ip 134.233.2.*     - ban all in a subnet
          @ban/ip 134.233.*.*     - even wider ban

        A single IP filter is easy to circumvent by changing the computer
        (also, some ISPs assign only temporary IPs to their users in the
        first placer. Widening the IP block filter with wildcards might be
        tempting, but remember that blocking too much may accidentally
        also block innocent users connecting from the same country and
        region.

        

@boot
~~~~~

-  ``key`` = ``@boot``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(boot) or perm(Wizards)``
-  `help\_category <HelpSystem.html>`_ = ``Admin``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @boot

        Usage
          @boot[/switches] <player obj> [: reason]

        Switches:
          quiet - Silently boot without informing player
          port - boot by port number instead of name or dbref

        Boot a player object from the server. If a reason is
        supplied it will be echoed to the user unless /quiet is set.
        

@delplayer (OOC command)
~~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@delplayer``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(delplayer) or perm(Immortals)``
-  `help\_category <HelpSystem.html>`_ = ``Admin``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        delplayer - delete player from server

        Usage:
          @delplayer[/switch] <name> [: reason]

        Switch:
          delobj - also delete the player's currently
                   assigned in-game object.

        Completely deletes a user from the server database,
        making their nick and e-mail again available.
        

@emit
~~~~~

-  ``key`` = ``@emit``
-  ``aliases`` = ``@remit, @pemit``
-  `locks <Locks.html>`_ = ``cmd:perm(emit) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Admin``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @emit

        Usage:
          @emit[/switches] [<obj>, <obj>, ... =] <message>
          @remit           [<obj>, <obj>, ... =] <message>
          @pemit           [<obj>, <obj>, ... =] <message>

        Switches:
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
-  `help\_category <HelpSystem.html>`_ = ``Admin``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @perm - set permissions

        Usage:
          @perm[/switch] <object> [= <permission>[,<permission>,...]]
          @perm[/switch] *<player> [= <permission>[,<permission>,...]]

        Switches:
          del : delete the given permission from <object> or <player>.
          player : set permission on a player (same as adding * to name)

        This command sets/clears individual permission strings on an object
        or player. If no permission is given, list all permissions on <object>.
        

@unban
~~~~~~

-  ``key`` = ``@unban``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(unban) or perm(Immortals)``
-  `help\_category <HelpSystem.html>`_ = ``Admin``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        remove a ban

        Usage:
          @unban <banid>

        This will clear a player name/ip ban previously set with the @ban
        command.  Use this command without an argument to view a numbered
        list of bans. Use the numbers in this list to select which one to
        unban.

        

@userpassword (OOC command)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@userpassword``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(newpassword) or perm(Wizards)``
-  `help\_category <HelpSystem.html>`_ = ``Admin``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @setpassword

        Usage:
          @userpassword <user obj> = <new password>

        Set a player's password.
        

@wall
~~~~~

-  ``key`` = ``@wall``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(wall) or perm(Wizards)``
-  `help\_category <HelpSystem.html>`_ = ``Admin``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @wall

        Usage:
          @wall <message>

        Announces a message to all connected players.
        

Building
--------

`Link to Python
module <https://code.google.com/p/evennia/source/browse/src/commands/default/building.py>`_

@alias
~~~~~~

-  ``key`` = ``@alias``
-  ``aliases`` = ``@setobjalias``
-  `locks <Locks.html>`_ = ``cmd:perm(setobjalias) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        Adding permanent aliases

        Usage:
          @alias <obj> [= [alias[,alias,alias,...]]]

        Assigns aliases to an object so it can be referenced by more
        than one name. Assign empty to remove all aliases from object.
        Observe that this is not the same thing as aliases
        created with the 'alias' command! Aliases set with @alias are
        changing the object in question, making those aliases usable
        by everyone.
        

@batchcode
~~~~~~~~~~

-  ``key`` = ``@batchcode``
-  ``aliases`` = ``@batchcodes``
-  `locks <Locks.html>`_ = ``cmd:superuser()``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        Build from batch-code file

        Usage:
         @batchcode[/interactive] <python path to file>

        Switch:
           interactive - this mode will offer more control when
                         executing the batch file, like stepping,
                         skipping, reloading etc.
           debug - auto-delete all objects that has been marked as
                   deletable in the script file (see example files for
                   syntax). This is useful so as to to not leave multiple
                   object copies behind when testing out the script.

        Runs batches of commands from a batch-code text file (*.py).

        

@batchcommands
~~~~~~~~~~~~~~

-  ``key`` = ``@batchcommands``
-  ``aliases`` = ``@batchcmd, @batchcommand``
-  `locks <Locks.html>`_ = ``cmd:perm(batchcommands) or superuser()``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        Build from batch-command file

        Usage:
         @batchcommands[/interactive] <python.path.to.file>

        Switch:
           interactive - this mode will offer more control when
                         executing the batch file, like stepping,
                         skipping, reloading etc.

        Runs batches of commands from a batch-cmd text file (*.ev).

        

@cmdsets
~~~~~~~~

-  ``key`` = ``@cmdsets``
-  ``aliases`` = ``@listcmsets``
-  `locks <Locks.html>`_ = ``cmd:perm(listcmdsets) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        list command sets on an object

        Usage:
          @cmdsets [obj]

        This displays all cmdsets assigned
        to a user. Defaults to yourself.
        

@copy
~~~~~

-  ``key`` = ``@copy``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(copy) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @copy - copy objects

        Usage:
          @copy[/reset] <original obj> [= new_name][;alias;alias..][:new_location] [,new_name2 ...]

        switch:
          reset - make a 'clean' copy off the object, thus
                  removing any changes that might have been made to the original
                  since it was first created.

        Create one or more copies of an object. If you don't supply any targets, one exact copy
        of the original object will be created with the name *_copy.
        

@cpattr
~~~~~~~

-  ``key`` = ``@cpattr``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(cpattr) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @cpattr - copy attributes

        Usage:
          @cpattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
          @cpattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
          @cpattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
          @cpattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]

        Switches:
          move - delete the attribute from the source object after copying.

        Example:
          @cpattr coolness = Anna/chillout, Anna/nicety, Tom/nicety
          ->
          copies the coolness attribute (defined on yourself), to attributes
          on Anna and Tom.

        Copy the attribute one object to one or more attributes on another object. If
        you don't supply a source object, yourself is used.
        

@create
~~~~~~~

-  ``key`` = ``@create``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(create) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @create - create new objects

        Usage:
          @create[/drop] objname[;alias;alias...][:typeclass], objname...

        switch:
           drop - automatically drop the new object into your current location (this is not echoed)
                  this also sets the new object's home to the current location rather than to you.

        Creates one or more new objects. If typeclass is given, the object
        is created as a child of this typeclass. The typeclass script is
        assumed to be located under game/gamesrc/types and any further
        directory structure is given in Python notation. So if you have a
        correct typeclass object defined in
        game/gamesrc/types/examples/red_button.py, you could create a new
        object of this type like this:

           @create button;red : examples.red_button.RedButton

        

@debug
~~~~~~

-  ``key`` = ``@debug``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(debug) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        Debug game entities

        Usage:
          @debug[/switch] <path to code>

        Switches:
          obj - debug an object
          script - debug a script

        Examples:
          @debug/script game.gamesrc.scripts.myscript.MyScript
          @debug/script myscript.MyScript
          @debug/obj examples.red_button.RedButton

        This command helps when debugging the codes of objects and scripts.
        It creates the given object and runs tests on its hooks.
        

@desc
~~~~~

-  ``key`` = ``@desc``
-  ``aliases`` = ``@describe``
-  `locks <Locks.html>`_ = ``cmd:perm(desc) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @desc - describe an object or room

        Usage:
          @desc [<obj> =] >description>

        Setts the "desc" attribute on an
        object. If an object is not given,
        describe the current room.
        

@destroy
~~~~~~~~

-  ``key`` = ``@destroy``
-  ``aliases`` = ``@del, @delete``
-  `locks <Locks.html>`_ = ``cmd:perm(destroy) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
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
           @destroy 5-10, flower, 45

        Destroys one or many objects. If dbrefs are used, a range to delete can be
        given, e.g. 4-10. Also the end points will be deleted.
        

@dig
~~~~

-  ``key`` = ``@dig``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(dig) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @dig - build and connect new rooms to the current one

        Usage:
          @dig[/switches] roomname[;alias;alias...][:typeclass]
                [= exit_to_there[;alias][:typeclass]]
                   [, exit_to_here[;alias][:typeclass]]

        Switches:
           tel or teleport - move yourself to the new room

        Examples:
           @dig kitchen = north;n, south;s
           @dig house:myrooms.MyHouseTypeclass
           @dig sheer cliff;cliff;sheer = climb up, climb down

        This command is a convenient way to build rooms quickly; it creates the new room and you can optionally
        set up exits back and forth between your current room and the new one. You can add as many aliases as you
        like to the name of the room and the exits in question; an example would be 'north;no;n'.
        

@examine
~~~~~~~~

-  ``key`` = ``@examine``
-  ``aliases`` = ``examine, @ex, ex, exam``
-  `locks <Locks.html>`_ = ``cmd:perm(examine) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        examine - detailed info on objects

        Usage:
          examine [<object>[/attrname]]
          examine [*<player>[/attrname]]

        Switch:
          player - examine a Player (same as adding *)
          raw - don't parse escape codes for data.

        The examine command shows detailed game info about an
        object and optionally a specific attribute on it.
        If object is not specified, the current location is examined.

        Append a * before the search string to examine a player.

        

@find
~~~~~

-  ``key`` = ``@find``
-  ``aliases`` = ``locate, @locate, search, @search, find``
-  `locks <Locks.html>`_ = ``cmd:perm(find) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        find objects

        Usage:
          @find[/switches] <name or dbref or *player> [= dbrefmin[-dbrefmax]]

        Switches:
          room - only look for rooms (location=None)
          exit - only look for exits (destination!=None)
          char - only look for characters (BASE_CHARACTER_TYPECLASS)

        Searches the database for an object of a particular name or dbref.
        Use *playername to search for a player. The switches allows for
        limiting object matches to certain game entities. Dbrefmin and dbrefmax
        limits matches to within the given dbrefs, or above/below if only one is given.
        

@help
~~~~~

-  ``key`` = ``@help``
-  ``aliases`` = ``@sethelp``
-  `locks <Locks.html>`_ = ``cmd:perm(PlayerHelpers)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @help - edit the help database

        Usage:
          @help[/switches] <topic>[,category[,locks]] = <text>

        Switches:
          add    - add or replace a new topic with text.
          append - add text to the end of topic with a newline between.
          merge  - As append, but don't add a newline between the old
                   text and the appended text.
          delete - remove help topic.
          force  - (used with add) create help topic also if the topic
                   already exists.

        Examples:
          @sethelp/add throw = This throws something at ...
          @sethelp/append pickpocketing,Thievery = This steals ...
          @sethelp/append pickpocketing, ,attr(is_thief) = This steals ...

        This command manipulates the help database. A help entry can be created,
        appended/merged to and deleted. If you don't assign a category, the "General"
        category will be used. If no lockstring is specified, default is to let everyone read
        the help file.

        

@home
~~~~~

-  ``key`` = ``@home``
-  ``aliases`` = ``@sethome``
-  `locks <Locks.html>`_ = ``cmd:perm(@home) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @home - control an object's home location

        Usage:
          @home <obj> [= home_location]

        The "home" location is a "safety" location for objects; they
        will be moved there if their current location ceases to exist. All
        objects should always have a home location for this reason.
        It is also a convenient target of the "home" command.

        If no location is given, just view the object's home location.
        

@link
~~~~~

-  ``key`` = ``@link``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(link) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @link - connect objects

        Usage:
          @link[/switches] <object> = <target>
          @link[/switches] <object> =
          @link[/switches] <object>

        Switch:
          twoway - connect two exits. For this to work, BOTH <object>
                   and <target> must be exit objects.

        If <object> is an exit, set its destination to <target>. Two-way operation
        instead sets the destination to the *locations* of the respective given
        arguments.
        The second form (a lone =) sets the destination to None (same as the @unlink command)
        and the third form (without =) just shows the currently set destination.
        

@lock
~~~~~

-  ``key`` = ``@lock``
-  ``aliases`` = ``lock, @locks, locks``
-  `locks <Locks.html>`_ = ``cmd: perm(@locks) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        lock - assign a lock definition to an object

        Usage:
          @lock <object>[ = <lockstring>]
          or
          @lock[/switch] object/<access_type>

        Switch:
          del - delete given access type
          view - view lock associated with given access type (default)

        If no lockstring is given, shows all locks on
        object.

        Lockstring is on the form
           'access_type:[NOT] func1(args)[ AND|OR][ NOT] func2(args) ...]
        Where func1, func2 ... valid lockfuncs with or without arguments.
        Separator expressions need not be capitalized.

        For example:
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
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @mvattr - move attributes

        Usage:
          @mvattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
          @mvattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
          @mvattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
          @mvattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]

        Switches:
          copy - Don't delete the original after moving.

        Move an attribute from one object to one or more attributes on another object. If
        you don't supply a source object, yourself is used.
        

@name
~~~~~

-  ``key`` = ``@name``
-  ``aliases`` = ``@rename``
-  `locks <Locks.html>`_ = ``cmd:perm(rename) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
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
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @open - create new exit

        Usage:
          @open <new exit>[;alias;alias..][:typeclass] [,<return exit>[;alias;..][:typeclass]]] = <destination>

        Handles the creation of exits. If a destination is given, the exit
        will point there. The <return exit> argument sets up an exit at the
        destination leading back to the current room. Destination name
        can be given both as a #dbref and a name, if that name is globally
        unique.

        

@script
~~~~~~~

-  ``key`` = ``@script``
-  ``aliases`` = ``@addscript``
-  `locks <Locks.html>`_ = ``cmd:perm(script) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        attach scripts

        Usage:
          @script[/switch] <obj> [= <script.path or scriptkey>]

        Switches:
          start - start all non-running scripts on object, or a given script only
          stop - stop all scripts on objects, or a given script only

        If no script path/key is given, lists all scripts active on the given
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
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @set - set attributes

        Usage:
          @set <obj>/<attr> = <value>
          @set <obj>/<attr> =
          @set <obj>/<attr>

        Sets attributes on objects. The second form clears
        a previously set attribute while the last form
        inspects the current value of the attribute
        (if any).

        The most common data to save with this command are strings and
        numbers. You can however also set Python primities such as lists,
        dictionaries and tuples on objects (this might be important for
        the functionality of certain custom objects).  This is indicated
        by you starting your value with one of {c'{n, {c"{n, {c({n, {c[{n  or {c{ {n.
        Note that you should leave a space after starting a dictionary ('{ ')
        so as to not confuse the dictionary start with a colour code like \{g.
        Remember that if you use Python primitives like this, you must
        write proper Python syntax too - notably you must include quotes
        around your strings or you will get an error.

        

@tel
~~~~

-  ``key`` = ``@tel``
-  ``aliases`` = ``@teleport``
-  `locks <Locks.html>`_ = ``cmd:perm(teleport) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        teleport object to another location

        Usage:
          @tel/switch [<object> =] <target location>

        Examples:
          @tel Limbo
          @tel/quiet box Limbo
          @tel/tonone box

        Switches:
          quiet  - don't echo leave/arrive messages to the source/target
                   locations for the move.
          intoexit - if target is an exit, teleport INTO
                     the exit object instead of to its destination
          tonone - if set, teleport the object to a None-location. If this
                   switch is set, <target location> is ignored.
                   Note that the only way to retrieve
                   an object from a None location is by direct #dbref
                   reference.

        Teleports an object somewhere. If no object is given, you yourself
        is teleported to the target location.     

@tunnel
~~~~~~~

-  ``key`` = ``@tunnel``
-  ``aliases`` = ``@tun``
-  `locks <Locks.html>`_ = ``cmd: perm(tunnel) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        dig in often-used directions

        Usage:
          @tunnel[/switch] <direction> [= roomname[;alias;alias;...][:typeclass]]

        Switches:
          oneway - do not create an exit back to the current location
          tel - teleport to the newly created room

        Example:
          @tunnel n
          @tunnel n = house;mike's place;green building

        This is a simple way to build using pre-defined directions:
         {wn,ne,e,se,s,sw,w,nw{n (north, northeast etc)
         {wu,d{n (up and down)
         {wi,o{n (in and out)
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
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @typeclass - set object typeclass

        Usage:
          @typclass[/switch] <object> [= <typeclass.path>]
          @type                     ''
          @parent                   ''

        Switch:
          reset - clean out *all* the attributes on the object -
                  basically making this a new clean object.
          force - change to the typeclass also if the object
                  already has a typeclass of the same name.
        Example:
          @type button = examples.red_button.RedButton

        View or set an object's typeclass. If setting, the creation hooks
        of the new typeclass will be run on the object. If you have
        clashing properties on the old class, use /reset. By default you
        are protected from changing to a typeclass of the same name as the
        one you already have, use /force to override this protection.

        The given typeclass must be identified by its location using
        python dot-notation pointing to the correct module and class. If
        no typeclass is given (or a wrong typeclass is given). Errors in
        the path or new typeclass will lead to the old typeclass being
        kept. The location of the typeclass module is searched from the
        default typeclass directory, as defined in the server settings.

        

@unlink
~~~~~~~

-  ``key`` = ``@unlink``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(unlink) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @unlink - unconnect objects

        Usage:
          @unlink <Object>

        Unlinks an object, for example an exit, disconnecting
        it from whatever it was connected to.
        

@wipe
~~~~~

-  ``key`` = ``@wipe``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(wipe) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``Building``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @wipe - clears attributes

        Usage:
          @wipe <object>[/attribute[/attribute...]]

        Example:
          @wipe box
          @wipe box/colour

        Wipes all of an object's attributes, or optionally only those
        matching the given attribute-wildcard search string.
        

Comms
-----

`Link to Python
module <https://code.google.com/p/evennia/source/browse/src/commands/default/comms.py>`_

@cboot (OOC command)
~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@cboot``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd: not pperm(channel_banned)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @cboot

        Usage:
           @cboot[/quiet] <channel> = <player> [:reason]

        Switches:
           quiet - don't notify the channel

        Kicks a player or object from a channel you control.

        

@ccreate (OOC command)
~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@ccreate``
-  ``aliases`` = ``channelcreate``
-  `locks <Locks.html>`_ = ``cmd:not pperm(channel_banned)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @ccreate
        channelcreate
        Usage:
         @ccreate <new channel>[;alias;alias...] = description

        Creates a new channel owned by you.
        

@cdesc (OOC command)
~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@cdesc``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:not pperm(channel_banned)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @cdesc - set channel description

        Usage:
          @cdesc <channel> = <description>

        Changes the description of the channel as shown in
        channel lists.
        

@cdestroy (OOC command)
~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@cdestroy``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd: not pperm(channel_banned)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @cdestroy

        Usage:
          @cdestroy <channel>

        Destroys a channel that you control.
        

@cemit (OOC command)
~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@cemit``
-  ``aliases`` = ``@cmsg``
-  `locks <Locks.html>`_ = ``cmd: not pperm(channel_banned)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @cemit - send a message to channel

        Usage:
          @cemit[/switches] <channel> = <message>

        Switches:
          noheader - don't show the [channel] header before the message
          sendername - attach the sender's name before the message
          quiet - don't echo the message back to sender

        Allows the user to broadcast a message over a channel as long as
        they control it. It does not show the user's name unless they
        provide the /sendername switch.

        

@channels (OOC command)
~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@channels``
-  ``aliases`` =
   ``comlist, channellist, all channels, channels, @clist, chanlist``
-  `locks <Locks.html>`_ = ``cmd: not pperm(channel_banned)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @clist

        Usage:
          @channels
          @clist
          comlist

        Lists all channels available to you, wether you listen to them or not.
        Use 'comlist" to only view your current channel subscriptions.
        

@cset (OOC command)
~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@cset``
-  ``aliases`` = ``@cclock``
-  `locks <Locks.html>`_ = ``cmd:not pperm(channel_banned)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @cset - changes channel access restrictions

        Usage:
          @cset <channel> [= <lockstring>]

        Changes the lock access restrictions of a channel. If no
        lockstring was given, view the current lock definitions.
        

@cwho (OOC command)
~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@cwho``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd: not pperm(channel_banned)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @cwho

        Usage:
          @cwho <channel>

        List who is connected to a given channel you have access to.
        

@imc2chan (OOC command)
~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@imc2chan``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ =
   ``cmd:serversetting(IMC2_ENABLED) and pperm(Immortals)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        imc2chan - link an evennia channel to imc2

        Usage:
          @imc2chan[/switches] <evennia_channel> = <imc2_channel>

        Switches:
          /disconnect - this clear the imc2 connection to the channel.
          /remove     -                "
          /list       - show all imc2<->evennia mappings

        Example:
          @imc2chan myimcchan = ievennia

        Connect an existing evennia channel to a channel on an IMC2
        network. The network contact information is defined in settings and
        should already be accessed at this point. Use @imcchanlist to see
        available IMC channels.

        

@imcinfo (OOC command)
~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@imcinfo``
-  ``aliases`` = ``@imcchanlist, @imcwhois, @imclist``
-  `locks <Locks.html>`_ =
   ``cmd: serversetting(IMC2_ENABLED) and pperm(Wizards)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        imcinfo - package of imc info commands

        Usage:
          @imcinfo[/switches]
          @imcchanlist - list imc2 channels
          @imclist -     list connected muds
          @imcwhois <playername> - whois info about a remote player

        Switches for @imcinfo:
          channels - as @imcchanlist (default)
          games or muds - as @imclist
          whois - as @imcwhois (requires an additional argument)
          update - force an update of all lists

        Shows lists of games or channels on the IMC2 network.
        

@irc2chan (OOC command)
~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@irc2chan``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ =
   ``cmd:serversetting(IRC_ENABLED) and pperm(Immortals)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @irc2chan - link evennia channel to an IRC channel

        Usage:
          @irc2chan[/switches] <evennia_channel> = <ircnetwork> <port> <#irchannel> <botname>

        Switches:
          /disconnect - this will delete the bot and remove the irc connection to the channel.
          /remove     -                                 "
          /list       - show all irc<->evennia mappings

        Example:
          @irc2chan myircchan = irc.dalnet.net 6667 myevennia-channel evennia-bot

        This creates an IRC bot that connects to a given IRC network and channel. It will
        relay everything said in the evennia channel to the IRC channel and vice versa. The
        bot will automatically connect at server start, so this comman need only be given once.
        The /disconnect switch will permanently delete the bot. To only temporarily deactivate it,
        use the @services command instead.
        

@rss2chan (OOC command)
~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@rss2chan``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ =
   ``cmd:serversetting(RSS_ENABLED) and pperm(Immortals)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @rss2chan - link evennia channel to an RSS feed

        Usage:
          @rss2chan[/switches] <evennia_channel> = <rss_url>

        Switches:
          /disconnect - this will stop the feed and remove the connection to the channel.
          /remove     -                                 "
          /list       - show all rss->evennia mappings

        Example:
          @rss2chan rsschan = http://code.google.com/feeds/p/evennia/updates/basic

        This creates an RSS reader  that connects to a given RSS feed url. Updates will be
        echoed as a title and news link to the given channel. The rate of updating is set
        with the RSS_UPDATE_INTERVAL variable in settings (default is every 10 minutes).

        When disconnecting you need to supply both the channel and url again so as to identify
        the connection uniquely.
        

addcom (OOC command)
~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``addcom``
-  ``aliases`` = ``aliaschan, chanalias``
-  `locks <Locks.html>`_ = ``cmd:not pperm(channel_banned)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        addcom - subscribe to a channel with optional alias

        Usage:
           addcom [alias=] <channel>

        Joins a given channel. If alias is given, this will allow you to
        refer to the channel by this alias rather than the full channel
        name. Subsequent calls of this command can be used to add multiple
        aliases to an already joined channel.
        

allcom (OOC command)
~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``allcom``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd: not pperm(channel_banned)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        allcom - operate on all channels

        Usage:
          allcom [on | off | who | destroy]

        Allows the user to universally turn off or on all channels they are on,
        as well as perform a 'who' for all channels they are on. Destroy deletes
        all channels that you control.

        Without argument, works like comlist.
        

delcom (OOC command)
~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``delcom``
-  ``aliases`` = ``delaliaschan, delchanalias``
-  `locks <Locks.html>`_ = ``cmd:not perm(channel_banned)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        delcom - unsubscribe from channel or remove channel alias

        Usage:
           delcom <alias or channel>

        If the full channel name is given, unsubscribe from the
        channel. If an alias is given, remove the alias but don't
        unsubscribe.
        

imctell (OOC command)
~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``imctell``
-  ``aliases`` = ``imc2tell, imc2page, imcpage``
-  `locks <Locks.html>`_ = ``cmd: serversetting(IMC2_ENABLED)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        imctell - send a page to a remote IMC player

        Usage:
          imctell User@MUD = <msg>
          imcpage      "

        Sends a page to a user on a remote MUD, connected
        over IMC2.
        

page (OOC command)
~~~~~~~~~~~~~~~~~~

-  ``key`` = ``page``
-  ``aliases`` = ``tell``
-  `locks <Locks.html>`_ = ``cmd:not pperm(page_banned)``
-  `help\_category <HelpSystem.html>`_ = ``Comms``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        page - send private message

        Usage:
          page[/switches] [<player>,<player>,... = <message>]
          tell        ''
          page <number>

        Switch:
          last - shows who you last messaged
          list - show your last <number> of tells/pages (default)

        Send a message to target user (if online). If no
        argument is given, you will get a list of your latest messages.
        

General
-------

`Link to Python
module <https://code.google.com/p/evennia/source/browse/src/commands/default/general.py>`_

@color
~~~~~~

-  ``key`` = ``@color``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        testing colors

        Usage:
          @color ansi|xterm256

        Print a color map along with in-mud color codes, while testing what is supported in your client.
        Choices are 16-color ansi (supported in most muds) or the 256-color xterm256 standard.
        No checking is done to determine your client supports color - if not you will
        see rubbish appear.
        

@encoding (OOC command)
~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@encoding``
-  ``aliases`` = ``@encode``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        encoding - set a custom text encoding

        Usage:
          @encoding/switches [<encoding>]

        Switches:
          clear - clear your custom encoding


        This sets the text encoding for communicating with Evennia. This is mostly an issue only if
        you want to use non-ASCII characters (i.e. letters/symbols not found in English). If you see
        that your characters look strange (or you get encoding errors), you should use this command
        to set the server encoding to be the same used in your client program.

        Common encodings are utf-8 (default), latin-1, ISO-8859-1 etc.

        If you don't submit an encoding, the current encoding will be displayed instead.
        

@ic (OOC command)
~~~~~~~~~~~~~~~~~

-  ``key`` = ``@ic``
-  ``aliases`` = ``@puppet``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        Switch control to an object

        Usage:
          @ic <character>

        Go in-character (IC) as a given Character.

        This will attempt to "become" a different object assuming you have
        the right to do so.  You cannot become an object that is already
        controlled by another player. In principle <character> can be
        any in-game object as long as you have access right to puppet it.
        

@ooc (OOC command)
~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@ooc``
-  ``aliases`` = ``@unpuppet``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @ooc - go ooc

        Usage:
          @ooc

        Go out-of-character (OOC).

        This will leave your current character and put you in a incorporeal OOC state.
        

@password (OOC command)
~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@password``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @password - set your password

        Usage:
          @password <old password> = <new password>

        Changes your password. Make sure to pick a safe one.
        

@quit (OOC command)
~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@quit``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        quit

        Usage:
          @quit

        Gracefully disconnect from the game.
        

access
~~~~~~

-  ``key`` = ``access``
-  ``aliases`` = ``hierarchy, groups``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        access - show access groups

        Usage:
          access

        This command shows you the permission hierarchy and
        which permission groups you are a member of.
        

drop
~~~~

-  ``key`` = ``drop``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        drop

        Usage:
          drop <obj>

        Lets you drop an object from your inventory into the
        location you are currently in.
        

get
~~~

-  ``key`` = ``get``
-  ``aliases`` = ``grab``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        get

        Usage:
          get <obj>

        Picks up an object from your location and puts it in
        your inventory.
        

help
~~~~

-  ``key`` = ``help``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        The main help command

        Usage:
          help <topic or command>
          help list
          help all

        This will search for help on commands and other
        topics related to the game.
        

help (OOC command)
~~~~~~~~~~~~~~~~~~

-  ``key`` = ``help``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        The main help command

        Usage:
          help <topic or command>
          help list
          help all

        This will search for help on commands and other
        topics related to the game.
        

home
~~~~

-  ``key`` = ``home``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(home) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        home

        Usage:
          home

        Teleports you to your home location.
        

inventory
~~~~~~~~~

-  ``key`` = ``inventory``
-  ``aliases`` = ``i, inv``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        inventory

        Usage:
          inventory
          inv

        Shows your inventory.
        

look
~~~~

-  ``key`` = ``look``
-  ``aliases`` = ``l, ls``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        look

        Usage:
          look
          look <obj>
          look *<player>

        Observes your location or objects in your vicinity.
        

look (OOC command)
~~~~~~~~~~~~~~~~~~

-  ``key`` = ``look``
-  ``aliases`` = ``l, ls``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        ooc look

        Usage:
          look

        This is an OOC version of the look command. Since a
        Player doesn't have an in-game existence, there is no
        concept of location or "self". If we are controlling
        a character, pass control over to normal look.

        

nick
~~~~

-  ``key`` = ``nick``
-  ``aliases`` = ``@nick, nicks, nickname, alias``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        Define a personal alias/nick

        Usage:
          nick[/switches] <nickname> = [<string>]
          alias             ''

        Switches:
          object   - alias an object
          player   - alias a player
          clearall - clear all your aliases
          list     - show all defined aliases (also "nicks" works)

        Examples:
          nick hi = say Hello, I'm Sarah!
          nick/object tom = the tall man

        A 'nick' is a personal shortcut you create for your own use. When
        you enter the nick, the alternative string will be sent instead.
        The switches control in which situations the substitution will
        happen. The default is that it will happen when you enter a
        command. The 'object' and 'player' nick-types kick in only when
        you use commands that requires an object or player as a target -
        you can then use the nick to refer to them.

        Note that no objects are actually renamed or changed by this
        command - the nick is only available to you. If you want to
        permanently add keywords to an object for everyone to use, you
        need build privileges and to use the @alias command.
        

pose
~~~~

-  ``key`` = ``pose``
-  ``aliases`` = ``:, emote``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        pose - strike a pose

        Usage:
          pose <pose text>
          pose's <pose text>

        Example:
          pose is standing by the wall, smiling.
           -> others will see:
          Tom is standing by the wall, smiling.

        Describe an action being taken. The pose text will
        automatically begin with your name.
        

say
~~~

-  ``key`` = ``say``
-  ``aliases`` = ``", '``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        say

        Usage:
          say <message>

        Talk to those in your current location.
        

who
~~~

-  ``key`` = ``who``
-  ``aliases`` = ``doing``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``General``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        who

        Usage:
          who
          doing

        Shows who is currently online. Doing is an alias that limits info
        also for those with all permissions.
        

System
------

`Link to Python
module <https://code.google.com/p/evennia/source/browse/src/commands/default/system.py>`_

@about
~~~~~~

-  ``key`` = ``@about``
-  ``aliases`` = ``@version``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``System``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @about - game engine info

        Usage:
          @about

        Display info about the game engine.
        

@objects
~~~~~~~~

-  ``key`` = ``@objects``
-  ``aliases`` = ``@listobjects, @stats, @db, @listobjs``
-  `locks <Locks.html>`_ = ``cmd:perm(listobjects) or perm(Builders)``
-  `help\_category <HelpSystem.html>`_ = ``System``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        Give a summary of object types in database

        Usage:
          @objects [<nr>]

        Gives statictics on objects in database as well as
        a list of <nr> latest objects in database. If not
        given, <nr> defaults to 10.
        

@py
~~~

-  ``key`` = ``@py``
-  ``aliases`` = ``!``
-  `locks <Locks.html>`_ = ``cmd:perm(py) or perm(Immortals)``
-  `help\_category <HelpSystem.html>`_ = ``System``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        Execute a snippet of python code

        Usage:
          @py <cmd>

        Separate multiple commands by ';'.  A few variables are made
        available for convenience in order to offer access to the system
        (you can import more at execution time).

        Available variables in @py environment:
          self, me                   : caller
          here                       : caller.location
          ev                         : the evennia API
          inherits_from(obj, parent) : check object inheritance

        {rNote: In the wrong hands this command is a severe security risk.
        It should only be accessible by trusted server admins/superusers.{n

        

@reload (OOC command)
~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@reload``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(reload) or perm(Immortals)``
-  `help\_category <HelpSystem.html>`_ = ``System``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        Reload the system

        Usage:
          @reload

        This restarts the server. The Portal is not
        affected. Non-persistent scripts will survive a @reload (use
        @reset to purge) and at_reload() hooks will be called.
        

@reset (OOC command)
~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@reset``
-  ``aliases`` = ``@reboot``
-  `locks <Locks.html>`_ = ``cmd:perm(reload) or perm(Immortals)``
-  `help\_category <HelpSystem.html>`_ = ``System``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        Reset and reboot the system

        Usage:
          @reset

        A cold reboot. This works like a mixture of @reload and @shutdown,
        - all shutdown hooks will be called and non-persistent scrips will
        be purged. But the Portal will not be affected and the server will
        automatically restart again.
        

@scripts
~~~~~~~~

-  ``key`` = ``@scripts``
-  ``aliases`` = ``@listscripts, @globalscript``
-  `locks <Locks.html>`_ = ``cmd:perm(listscripts) or perm(Wizards)``
-  `help\_category <HelpSystem.html>`_ = ``System``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        Operate and list global scripts, list all scrips.

        Usage:
          @scripts[/switches] [<obj or scriptid or script.path>]

        Switches:
          start - start a script (must supply a script path)
          stop - stops an existing script
          kill - kills a script - without running its cleanup hooks
          validate - run a validation on the script(s)

        If no switches are given, this command just views all active
        scripts. The argument can be either an object, at which point it
        will be searched for all scripts defined on it, or an script name
        or dbref. For using the /stop switch, a unique script dbref is
        required since whole classes of scripts often have the same name.

        Use @script for managing commands on objects.
        

@server
~~~~~~~

-  ``key`` = ``@server``
-  ``aliases`` = ``@serverload, @serverprocess``
-  `locks <Locks.html>`_ = ``cmd:perm(list) or perm(Immortals)``
-  `help\_category <HelpSystem.html>`_ = ``System``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        server load and memory statistics

        Usage:
           @serverload

        This command shows server load statistics and dynamic memory
        usage.

        Some Important statistics in the table:

        {wServer load{n is an average of processor usage. It's usually
        between 0 (no usage) and 1 (100% usage), but may also be
        temporarily higher if your computer has multiple CPU cores.

        The {wResident/Virtual memory{n displays the total memory used by
        the server process.

        Evennia {wcaches{n all retrieved database entities when they are
        loaded by use of the idmapper functionality. This allows Evennia
        to maintain the same instances of an entity and allowing
        non-persistent storage schemes. The total amount of cached objects
        are displayed plus a breakdown of database object types. Finally,
        {wAttributes{n are cached on-demand for speed. The total amount of
        memory used for this type of cache is also displayed.

        

@service
~~~~~~~~

-  ``key`` = ``@service``
-  ``aliases`` = ``@services``
-  `locks <Locks.html>`_ = ``cmd:perm(service) or perm(Immortals)``
-  `help\_category <HelpSystem.html>`_ = ``System``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @service - manage services

        Usage:
          @service[/switch] <service>

        Switches:
          list   - shows all available services (default)
          start  - activates a service
          stop   - stops a service

        Service management system. Allows for the listing,
        starting, and stopping of services. If no switches
        are given, services will be listed.
        

@shutdown (OOC command)
~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``@shutdown``
-  ``aliases`` = ``<None>``
-  `locks <Locks.html>`_ = ``cmd:perm(shutdown) or perm(Immortals)``
-  `help\_category <HelpSystem.html>`_ = ``System``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @shutdown

        Usage:
          @shutdown [announcement]

        Gracefully shut down both Server and Portal.
        

@time
~~~~~

-  ``key`` = ``@time``
-  ``aliases`` = ``@uptime``
-  `locks <Locks.html>`_ = ``cmd:perm(time) or perm(Players)``
-  `help\_category <HelpSystem.html>`_ = ``System``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        @time

        Usage:
          @time

        Server local time.
        

Unloggedin
----------

`Link to Python
module <https://code.google.com/p/evennia/source/browse/src/commands/default/unloggedin.py>`_

\_\_unloggedin\_look\_command (Unloggedin command)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``__unloggedin_look_command``
-  ``aliases`` = ``look, l``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``Unloggedin``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        This is an unconnected version of the look command for simplicity.

        This is called by the server and kicks everything in gear.
        All it does is display the connect screen.
        

connect (Unloggedin command)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``connect``
-  ``aliases`` = ``co, conn, con``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``Unloggedin``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        Connect to the game.

        Usage (at login screen):
          connect playername password
          connect "player name" "pass word"

        Use the create command to first create an account before logging in.

        If you have spaces in your name, enclose it in quotes.
        

create (Unloggedin command)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``create``
-  ``aliases`` = ``cr, cre``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``Unloggedin``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        Create a new account.

        Usage (at login screen):
          create <playername> <password>
          create "player name" "pass word"

        This creates a new player account.

        If you have spaces in your name, enclose it in quotes.
        

help (Unloggedin command)
~~~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``help``
-  ``aliases`` = ``h, ?``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``Unloggedin``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        This is an unconnected version of the help command,
        for simplicity. It shows a pane of info.
        

quit (Unloggedin command)
~~~~~~~~~~~~~~~~~~~~~~~~~

-  ``key`` = ``quit``
-  ``aliases`` = ``q, qu``
-  `locks <Locks.html>`_ = ``cmd:all()``
-  `help\_category <HelpSystem.html>`_ = ``Unloggedin``
-  [`HelpSystem <HelpSystem.html>`_\ #Auto-help\_system Auto-help]
   (``__doc__ string``) =

::

        We maintain a different version of the quit command
        here for unconnected players for the sake of simplicity. The logged in
        version is a bit more complicated.
        

