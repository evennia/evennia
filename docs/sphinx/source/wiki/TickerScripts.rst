Ticker Scripts ("Heartbeats")
=============================

A common way to implement a dynamic MUD is by using "tickers", also
known as "heartbeats". Tickers are very common or even unavoidable in
other mud code bases, where many systems are hard coded to rely on the
concept of the global 'tick'. In Evennia this is very much up to your
game and which requirements you have. `Scripts <Scripts.html>`_ are
powerful enough to act as any type of counter you want.

When \_not\_ to use tickers
---------------------------

Even if you are used to habitually relying on tickers in other code
bases, stop and think about what you really need them for. Notably you
should think very, *very* hard before implementing a ticker to *catch
changes in something that rarely changes*. Think about it - you might
have to run the ticker every second to react to changes fast enough.
This means that most of the time *nothing* will have changed. You are
doing pointless calls (since skipping the call gives the same result as
doing it). Making sure nothing's changed might even be a tad expensive
depending on the complexity of your system. Not to mention that you
might need to run the check on every object in the database. Every
second. Just to maintain status quo.

Rather than checking over and over on the off-chance that something
changed, consider a more proactive approach. Can you maybe implement
your rarely changing system to *itself* report its change *whenever* it
happens? It's almost always much cheaper/efficient if you can do things
"on demand". Evennia itself uses hook methods all over for this very
reason. The only real "ticker"-like thing in the default set is the one
that saves the uptime (which of course *always* changes every call).

So, in summary, if you consider a ticker script that will fire very
often but which you expect to do nothing 99% of the time, ponder if you
can handle things some other way.

Ticker example - night/day system
=================================

Let's take the example of a night/day system. The way we want to use
this is to have all outdoor rooms echo time-related messages to the
room. Things like "The sun sets", "The church bells strike midnight" and
so on.

One could imagine every `Room <Objects.html>`_ in the game having a
script running on themselves that fire regularly. It's however much
better (easier to handle and using a lot less computing resources) to
use a single, global, ticker script. You create a "global" Script the
way you would any Script except you don't assign it to any particular
object.

To let objects use this global ticker, we will utilize a *subscription
model*. In short this means that our Script holds an internal list of
"subscribing" rooms. Whenever the Script fires it loops through this
list and calls a given method on the subscribed object.

::

    from ev import Script
    class TimeTicker(Script):
        """
        This implements a subscription model
        """
        def at_script_creation(self):
            "Called when script is created"
            self.key = "daynight_ticker"
            self.interval = 60 * 60 * 2 # every two hours
            self.persistent = True 
            # storage of subscriptions
            self.db.subscriptions = []
        def subscribe(self, obj):
            "add object to subscription"
            if obj not in self.db.subscriptions:
                self.db.subscriptions.append(obj)
        def unsubscribe(self, obj):
            "remove object from subscription"
            try:
                del_ind = self.db.subscriptions.index(obj)
                del self.db.subscriptions[del_ind]
            except ValueError:
                pass
        def list_subscriptions(self):
            "echo all subscriptions"
            return self.db.subscriptions        
        def at_repeat(self):
            "called every self.interval seconds"
            for obj in self.db.subscriptions:
                obj.echo_daynight()

This depends on your subscribing weather rooms defining the
``echo_daynight()`` method (presumably outputting some sort of message).

It's worth noting that this simple recipe can be used for all sorts of
tickers objects. Rooms are maybe not likely to unsubscribe very often,
but consider a mob that "deactivates" when Characters are not around for
example.

The above TimeTicker-example could be further optimized. All subscribed
rooms are after all likely to echo the same time related text. So this
text can be pre-set already at the Script level and echoed to each room
directly. This way the subscribed objects won't need a custom
``echo_daynight()`` method at all.

Here's the more efficient example (only showing the new stuff).

::

    ...
    ECHOES = ["The sun rises in the east.", "It's mid-morning", 
             "It's mid-day",  ...]
    class TimerTicker(Script):
        ...
        def at_script_creation(self):
            ...    
            self.db.timeindex = 0
            ...
        def at_repeat(self):
            "called every self.repeat seconds"
            echo = ECHOES[self.db.timeindex]
            # msg_contents() is a standard method, so this
            # ticker works with any object.
            for obj in self.db.subscriptions: 
                obj.msg_contents(echo)
            # resetting/stepping the counter
            if self.db.timeindex == len(ECHOES) - 1:
                self.db.timeindex = 0
            else:
                self.db.timeindex += 1

Note that this ticker is unconnected to Evennia's default global in-game
time script, and will thus be out of sync with that. A more advanced
example would entail this script checking the current game time (in
``at_script_creation()`` or in ``at_start()``) so it can pick a matching
starting point in its cycle.

Testing the night/day ticker
----------------------------

Tickers are really intended to be created and handled from your custom
commands or in other coded systems. An "outdoor" room typeclass would
probably subscribe to the ticker itself from its
``at_object_creation()`` hook. Same would be true for mobs and other
objects that could respond to outside stimuli (such as the presence of a
player) in order to subscribe/unsubscribe.

There is no way to create a global script using non-superuser commands,
and even if you could use ``@script`` to put it on an object just to
test things out, you also need a way to subscribe objects to it.

With ``@py`` this would be something like this:

    ::

         @py ev.create_script(TimeTicker) # if persistent=True, this only needs to be done once 
         @py ev.search_script("daynight_ticker").subscribe(self.location)
         

If you think you will use these kind of ticker scripts a lot, you might
want to create your own command for adding/removing subscriptions to
them. Here is a complete example:

::

    import ev
    class CmdTicker(ev.default_cmds.MuxCommand):
        """
        adds/remove an object to a given ticker

        Usage: 
          @ticker[/switches] tickerkey [= object]
        Switches:
          add (default) - subscribe object to ticker
          del           - unsubscribe object from ticker

        This adds an object to a named ticker Script, 
        if such a script exists. Such a script must have
        subsribe/unsubscripe functionality. If no object is 
        supplied, a list of subscribed objects for this ticker
        will be returned instead. 
        """
        key = "@ticker"
        locks = "cmd:all()"
        help_category = "Building"

        def func(self):
            if not self.args:
                self.caller.msg("Usage: @ticker[/switches] tickerkey [= object]")
                return
            tickerkey = self.lhs
            # find script
            script = ev.search_scripts(tickerkey)      
            if not script:
                self.caller.msg("Ticker %s could not be found." % tickerkey)        
                return 
            # all ev.search_* methods always return lists
            script = script[0]
            # check so the API is correct 
            if not (hasattr(script, "subscribe") 
                    and hasattr(script, "unsubscribe")
                    and hasattr(script, "list_subscriptions"):
                self.caller.msg("%s can not be subscribed to." % tickerkey)
                return
            if not self.rhs: 
                # no '=' found, just show the subs               
                subs = [o.key for o in script.list_subscripionts()]
                self.caller.msg(", ".join(subs))
                return 
            # get the object to add
            obj = self.caller.search(self.rhs)        
            if not obj:
                # caller.search handles error messages
                return
            elif 'del' in self.switches: 
                # remove a sub
                script.unsubscribe(obj)
                self.caller.msg("Unsubscribed %s from %s." % (obj.key, tickerkey)
            else:
                # default - add subscription
                script.subscribe(obj)
                self.caller.msg("Subscribed %s to ticker %s." % (obj.key, tickerkey))

This looks longer than it is, most of the length comes from comments and
the doc string.
