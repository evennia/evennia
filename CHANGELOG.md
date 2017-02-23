# Evennia Changelog
## Feb 2017:
New devel branch created, to lead up to Evennia 0.7.

## Dec 2016:
Lots of bugfixes and considerable uptick in contributors. Unittest coverage
and PEP8 adoption and refactoring.

## May 2016:
Evennia 0.6 with completely reworked Out-of-band system, making 
the message path completely flexible and built around input/outputfuncs.
A completely new webclient, split into the evennia.js library and a 
gui library, making it easier to customize.

## Feb 2016:
Added the new EvMenu and EvMore utilities, updated EvEdit and cleaned up
a lot of the batchcommand functionality. Started work on new Devel branch.

## Sept 2015:
Evennia 0.5. Merged devel branch, full library format implemented.

## Feb 2015:
Development currently in devel/ branch. Moved typeclasses to use
django's proxy functionality. Changed the Evennia folder layout to a
library format with a stand-alone launcher, in preparation for making
an 'evennia' pypy package and using versioning. The version we will
merge with will likely be 0.5. There is also work with an expanded
testing structure and the use of threading for saves. We also now
use Travis for automatic build checking. 

## Sept 2014:
Updated to Django 1.7+ which means South dependency was dropped and
minimum Python version upped to 2.7. MULTISESSION_MODE=3 was added
and the web customization system was overhauled using the latest 
functionality of django. Otherwise, mostly bug-fixes and 
implementation of various smaller feature requests as we got used
to github. Many new users have appeared. 

## Jan 2014:
Moved Evennia project from Google Code to github.com/evennia/evennia.

## Nov 2013:
Moved the internal webserver into the Server and added support for
out-of-band protocols (MSDP initially). This large development push
also meant fixes and cleanups of the way attributes were handled.
Tags were added, along with proper handlers for permissions, nicks
and aliases.

## May 2013:
Made players able to control more than one Character at the same
time, through the MULTISESSION_MODE=2 addition. This lead to a lot
of internal changes for the server.

## Oct 2012:
Changed Evennia from the Modified Artistic 1.0 license to the more
standard and permissive BSD license. Lots of updates and bug fixes as
more people start to use it in new ways. Lots of new caching and
speed-ups.

## March 2012:
Evennia's API has changed and simplified slightly in that the
base-modules where removed from game/gamesrc. Instead admins are
encouraged to explicitly create new modules under game/gamesrc/ when
they want to implement their game - gamesrc/ is empty by default
except for the example folders that contain template files to use for
this purpose. We also added the ev.py file, implementing a new, flat
API.  Work is ongoing to add support for mud-specific telnet
extensions, notably the MSDP and GMCP out-of-band extensions.  On the
community side, evennia's dev blog was started and linked on planet
Mud-dev aggregator.

## Nov 2011:
After creating several different proof-of-concept game systems (in
contrib and privately) as well testing lots of things to make sure the
implementation is basically sound, we are declaring Evennia out of
Alpha. This can mean as much or as little as you want, admittedly -
development is still heavy but the issue list is at an all-time low
and the server is slowly stabilizing as people try different things
with it. So Beta it is!

## Aug 2011:
Split Evennia into two processes: Portal and Server. After a lot of
work trying to get in-memory code-reloading to work, it's clear this
is not Python's forte - it's impossible to catch all exceptions,
especially in asynchronous code like this.  Trying to do so results in
hackish, flakey and unstable code. With the Portal-Server split, the
Server can simply be rebooted while players connected to the Portal
remain connected. The two communicates over twisted's AMP protocol.

## May 2011:
The new version of Evennia, originally hitting trunk in Aug2010, is
maturing. All commands from the pre-Aug version, including IRC/IMC2
support works again. An ajax web-client was added earlier in the year,
including moving Evennia to be its own webserver (no more need for
Apache or django-testserver). Contrib-folder added.

## Aug 2010:
Evennia-griatch-branch is ready for merging with trunk. This marks a
rather big change in the inner workings of the server, such as the
introduction of TypeClasses and Scripts (as compared to the old
ScriptParents and Events) but should hopefully bring everything
together into one consistent package as code development continues.

## May 2010:
Evennia is currently being heavily revised and cleaned from
the years of gradual piecemeal development. It is thus in a very
'Alpha' stage at the moment. This means that old code snippets
will not be backwards compatabile. Changes touch almost all
parts of Evennia's innards, from the way Objects are handled
to Events, Commands and Permissions.

## April 2010:
Griatch takes over Maintainership of the Evennia project from
the original creator Greg Taylor.

(Earlier revisions, with previous maintainer, go back to 2005)


# Contact, Support and Development

Make a post to the mailing list or chat us up on IRC. We also have a
bug tracker if you want to report bugs. Finally, if you are willing to
help with the code work, we much appreciate all help!  Visit either of
the following resources:

* Evennia Webpage
  http://evennia.com
* Evennia manual (wiki)
  https://github.com/evennia/evennia/wiki
* Evennia Code Page (See INSTALL text for installation)
  https://github.com/evennia/evennia
* Bug tracker
  https://github.com/evennia/evennia/issues
* IRC channel
  visit channel #evennia on irc.freenode.com
  or the webclient: http://tinyurl.com/evchat
