Evennia Server Configurations
=============================

Evennia runs out of the box without any changes to its settings. But
there are several important ways to customize the server and expand it
with your own plugins.

Settings file
-------------

The "Settings" file referenced throughout the documentation is the file
``game/settings.py``. This is automatically created on the first run of
``manage.py syncdb`` (see the `GettingStarted <GettingStarted.html>`_
page). The settings file is actually a normal Python module. It's pretty
much empty from the start, it just imports all default values from
``src/settings_default.py`` into itself.

You should never edit ``src/settings_default.py``. Rather you should
copy&paste the variables you want to change into ``settings.py`` and
edit them there. This will overload the previously imported defaults.

In code, the settings is accessed through

::

    from django.conf import settings
     # or (shorter):
    from ev import settings
     # example:
    servername = settings.SERVER_NAME

Each setting appears as a property on the imported ``settings`` object.
You can also explore all possible options with ``ev.settings_full``
(this also includes advanced Django defaults that are not not touched in
default Evennia).

It should be pointed out that when importing ``settings`` into your code
like this, it will be *read only*. You cannot edit your settings in
code. The only way to change an Evennia setting is to edit
``game/settings.py`` directly. You most often need to restart the server
(possibly also the Portal) before a changed setting becomes available.

\`game/gamesrc/conf\` directory
-------------------------------

The ``game/gamesrc/conf/`` directory contains module templates for
customizing Evennia. Common for all these is that you should *copy* the
template up one level (to ``game/gamesrc/conf/``) and edit the copy, not
the original. You then need to change your settings file to point the
right variable at your new module. Each template header describes
exactly how to use it and which settings variable needs to be changed
for Evennia to be able to locate it.

-  ``at_initial_setup.py`` - this allows you to add a custom startup
   method to be called (only) the very first time Evennia starts (at the
   same time as user #1 and Limbo is created). It can be made to start
   your own global scripts or set up other system/world-related things
   your game needs to have running from the start.
-  ``at_server_startstop.py`` - this module contains two functions that
   Evennia will call every time the Server starts and stops respectively
   - this includes stopping due to reloading and resetting as well as
   shutting down completely. It's a useful place to put custom startup
   code for handlers and other things that must run in your game but
   which has no database persistence.
-  ``connection_screens.py`` - all global string variables in this
   module are interpreted by Evennia as a greeting screen to show when a
   Player first connects. If more than one string variable is present in
   the module a random one will be picked.
-  ``lockfuncs.py`` - this is one of many possible modules to hold your
   own "safe" *lock functions* to make available to Evennia's `lock
   system <Locks.html>`_.
-  ``mssp.py`` - this holds meta information about your game. It is used
   by MUD search engines (which you often have to register with) in
   order to display what kind of game you are running along with
   statistics such as number of online players and online status.
-  ``portal_services_plugin.py`` - this allows for adding your own
   custom servies/protocols to the Portal. It must define one particular
   function that will be called by Evennia at startup. There can be any
   number of service plugin modules, all will be imported and used if
   defined. More info can be found
   `here <http://code.google.com/p/evennia/wiki/SessionProtocols#Adding_custom_Protocols>`_.
-  ``server_services_plugin.py`` - this is equivalent to the previous
   one, but used for adding new services to the Server instead. More
   info can be found
   `here <http://code.google.com/p/evennia/wiki/SessionProtocols#Adding_custom_Protocols>`_.

Some other Evennia systems can be customized by plugin modules but has
no explicit template in ``conf/examples``:

-  *command parser* - a custom module can be used to totally replace
   Evennia's default command parser. All this does is to split the
   incoming string into "command name" and "the rest". It also handles
   things like error messages for no-matches and multiple-matches among
   other things that makes this more complex than it sounds. The default
   parser is *very* generic, so you are most often best served by
   modifying things further down the line (on the command parse level)
   than here.
-  *search-return handler* - this can be used to replace how Evennia
   handles search results from most of Evennia's in-game searches (most
   importantly ``self.caller.search`` in commands). It handles the
   echoing of errors.
-  *multimatch handler* - this plugin replaces the handling of multiple
   match errors in searching. By default it allows for separating
   between same-named matches by use of numbers. Like understanding that
   "2-ball" should match the second "ball" object if there are two of
   them.

!ServerConf
-----------

There is a special database model called ServerConf that stores server
internal data and settings such as current player count (for interfacing
with the webserver), startup status and many other things. It's rarely
of use outside the server core itself but may be good to know about if
you are an Evennia developer.
