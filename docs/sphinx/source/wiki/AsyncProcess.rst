Asynchronous code
=================

*This is considered an advanced topic, probably not useful for most
users.*

Synchronous versus Asynchronous
-------------------------------

Most code operate *synchronously*. This means that each statement in
your code gets processed and finishes before the next can begin. This
makes for easy-to-understand code. It is also a *requirement* in many
cases - a subsequent piece of code often depend on something calculated
or defined in a previous statement.

Consider this piece of code:

::

    print "before call ..." long_running_function() print "after call ..."

When run, this will print ``"before call ..."``, after which the
``long_running_function`` gets to work for however long time. Only once
that is done, the system prints ``"after call ..."``. Easy and logical
to follow. Most of Evennia work in this way. Most of the time we want to
make sure that commands get executed in strict order after when they
where entered.

The main problem is that Evennia is a multi-user server. It swiftly
switches between dealing with player input in the order it is sent to
it. So if one user, say, run a command containing that
``long_running_function``, *all* other players are effectively forced to
wait until it finishes ... hardly an ideal solution.

Now, it should be said that on a modern computer system this is rarely
an issue. Very few commands run so long that other users notice it. And
as mentioned, most of the time you *want* to enforce all commands to
occur in strict sequence.

When delays do become noticeable and you don't care which order the
command actually completes, you can run it *asynchronously*. This makes
use of the ``run_async()`` function in ``src/utils/utils.py``.

::

    from src.utils import utils print "before call ..." utils.run_async(long_running_function) print "after call ..."

Now, when running this you will find that the program will not wait
around for ``long_running_function`` to finish. Infact you will see
``"before call ..."`` and ``"after call ..."`` printed out right away.
The long-running function will run in the background and you (and other
users) can go on as normal.

Customizing asynchronous operation
----------------------------------

A complication with using asynchronous calls is what to do with the
result from that call. What if ``long_running_function`` returns a value
that you need? It makes no real sense to put any lines of code after the
call to try to deal with the result from ``long_running_function`` above
- as we saw the ``"after call ..."`` got printed long before
``long_running_function`` was finished, making that line quite pointless
for processing any data from the function. Instead one has to use
*callbacks*.

``utils.run_async`` takes two optional arguments, ``at_return`` and
``at_err``. Both of these should be function defitions. Each will be
called automatically.

-  ``at_return(r)`` (the *callback*) is called when the asynchronous
   function (``long_running_function`` above) finishes successfully. The
   argument ``r`` will then be the return value of that function (or
   ``None``). Example:

::

    def at_return(r):      print r

-  ``at_err(e)`` (the *errback*) is called if the asynchronous function
   fails and raises an exception. This exception is passed to the
   errback wrapped in a *Failure* object ``e``. If you do not supply an
   errback of your own, Evennia will automatically add one that silently
   writes errors to the evennia log. An example of an errback is found
   below:

::

    def at_err(e):   
        print "There was an error:", str(e)

An example of making an asynchronous call from inside a
`Command <Commands.html>`_ definition:

::

    from src.utils import utils from game.gamesrc.commands.basecommand import Command      class CmdAsync(Command):   key = "asynccommand"   def func(self):                     def long_running_function():              #[... lots of time-consuming code              return final_value                def at_return(r):            self.caller.msg("The final value is %s" % r)       def at_err(e):            self.caller.msg("There was an error: %s" % e)       # do the async call, setting all callbacks        utils.run_async(long_running_function, at_return, at_err)

That's it - from here on we can forget about ``long_running_function``
and go on with what else need to be done. *Whenever* it finishes, the
``at_return`` function will be called and the final value will pop up
for us to see. If not we will see an error message.

Assorted notes
--------------

Note that the ``run_async`` will try to launch a separate thread behind
the scenes. Some databases, notably our default database SQLite3, does
*not* allow concurrent read/writes. So if you do a lot of database
access (like saving to an Attribute) in your function, your code might
actually run *slower* using this functionality if you are not careful.
Extensive real-world testing is your friend here.

Overall, be careful with choosing when to use asynchronous calls. It is
mainly useful for large administration operations that has no direct
influence on the game world (imports and backup operations come to
mind). Since there is no telling exactly when an asynchronous call
actually ends, using them for in-game commands is to potentially invite
confusion and inconsistencies (and very hard-to-reproduce bugs).

The very first synchronous example above is not *really* correct in the
case of Twisted, which is inherently an asynchronous server. Notably you
might find that you will *not* see the first ``before call ...`` text
being printed out right away. Instead all texts could end up being
delayed until after the long-running process finishes. So all commands
will retain their relative order as expected, but they may appear with
delays or in groups.

Further reading
---------------

Technically, ``run_async`` is just a very thin and simplified wrapper
around a `Twisted
Deferred <http://twistedmatrix.com/documents/9.0.0/core/howto/defer.html>`_
object; the wrapper sets up a separate thread and assigns a default
errback also if none is supplied. If you know what you are doing there
is nothing stopping you from bypassing the utility function, building a
more sophisticated callback chain after your own liking.
