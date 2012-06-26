Sometimes it's just not worth the grief ...
===========================================

Whether due to abuse, blatant breaking of your rules, or some other
reason you will eventually find no other recourse but to kick out a
particularly troublesome player. The default command set has admin tools
to handle this, primarily ``@ban, @unban`` and ``@boot``.

Creating a ban
==============

Say we have a troublesome player "YouSuck" - this is a guy that refuse
common courtesy - an abusive and spammy account that is clearly created
by some bored internet hooligan only to cause grief. You have tried to
be nice. Now you just want this troll gone.

Name ban
--------

The easiest is to block the account YouSuck from ever connecting again.

::

     @ban YouSuck

This will lock the name YouSuck (as well as 'yousuck' and any other
combination), and next time they try to log in with this name the server
will not let them!

You can also give a reason so you remember later why this was a good
thing (the banned player will never see this)

::

     @ban YouSuck:This is just a troll.

If you are sure this is just a spam account, you might even consider
deleting the player account outright:

::

     @delplayer YouSuck

Generally banning the name is the easier and safer way to stop the use
of an account -- if you change your mind you can always remove the block
later whereas a deletion is permanent.

IP ban
------

Just because you block YouSuck's name might not mean the trolling human
behind that account gives up. They can just create a new account
YouSuckMore and be back at it. One way to make things harder for them is
to tell the server to not allow connections from their particular IP
address.

First, when the offending player is online, check which IP address they
use. This you can do with the ``who`` command, which will show you
something like this:

::

     Player Name     On for     Idle     Room     Cmds     Host          
     YouSuck         01:12      2m       22       212      237.333.0.223 

The "Host" bit is the IP address from which the player is connecting.
Use this to define the ban instead of the name:

::

     @ban 237.333.0.223

This will stop YouSuck connecting from his computer. Note however that
IP addresses might change easily - either due to how the player's
Internet Service Provider operates or by the user simply changing
computer. You can make a more general ban by putting asterisks ``*`` as
wildcards for the groups of three digits in the address. So if you
figure out that YouSuck mainly connects from 237.333.0.223,
237.333.0.225 and 237.333.0.256 (only changes in the local subnet), it
might be an idea to put down a ban like this to include any number in
that subnet:

::

     @ban 237.333.0.*

You should combine the IP ban with a name-ban too of course, so the
account YouSuck is truly locked regardless of from where they connect.

Be careful with too general IP bans however (more asterisks above). If
you are unlucky you could be blocking out innocent players who just
happen to connect from the same subnet as the offender.

Booting
=======

YouSuck is not really noticing all this banning yet though - and won't
until having logged out and tries to log back in again. Let's help the
troll along.

::

     @boot YouSuck

Good riddance. You can give a reason for booting too (to be echoed to
the player before getting kicked out).

::

     @boot YouSuck:Go troll somewhere else.

Lifting a ban
=============

Give the ``@unban`` (or ``@ban``) command without any arguments and you
will see a list of all currently active bans:

::

    Active bans
    id   name/ip       date                      reason 
    1    yousuck       Fri Jan 3 23:00:22 2020   This is just a Troll.
    2    237.333.0.*   Fri Jan 3 23:01:03 2020   YouSuck's IP.

Use the ``id`` from this list to find out which ban to lift.

::

     @unban 2
      
    Cleared ban 2: 237.333.0.*

