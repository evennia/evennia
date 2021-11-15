copyrights: _Image: Franco Nero as the twisted gunslinger Django_

---

### [Combining Twisted and Django](https://evennia.blogspot.com/2012/08/combining-twisted-and-django.html)

[![](https://3.bp.blogspot.com/-Spum6fodLn0/TqPvuMp20mI/AAAAAAAAAIc/LteJztyYZXY/s320/DJango.jpg)](https://3.bp.blogspot.com/-Spum6fodLn0/TqPvuMp20mI/AAAAAAAAAIc/LteJztyYZXY/s1600/DJango.jpg)

Newcomers to Evennia sometimes misunderstand it as being a "Django mud codebase somehow using Twisted". The correct description is rather that Evennia is a "Twisted-based mud server using Django". Allow me to elaborate.  
  
A mud/mux/moo/mu* is per definition a multi-user online game system. All these users need to co-exist on the server. If one player does something, other players shouldn't have to (noticeably) wait for that something to end before they can do anything. Furthermore it's important for the database schema to be easy to handle and upgrade. Finally, in a modern game, internet presence and web browser access is becoming a must. We combine two frameworks to achieve this.  
  

### Two frameworks combined

  
_[Twisted](http://twistedmatrix.com/trac/)_ is a asynchronous Python framework. "Asynchronous" in this context means, very simplified, that Twisted chops up code execution into as small bits as the code lets it. It then flips through these snippets rapidly, executing each in turn. The result is the illusion of everything happening at the same time. The asynchronous operation is the basis for the framework, but it also helps that twisted makes it easy to support (and create) a massive range of different network protocols.  
  
_[Django](https://www.djangoproject.com/)_ implements a very nice abstract Python API for accessing a variety of SQL-like databases. It makes it very convenient to maintain the database schema (not to mention that _django-South_ gives us easy database migrations). The fact that Django is really a web framework also makes it easy to offer various web features. There is for example an "admin site" that comes with Django. It allows to modify the database graphically (in Evennia's case the admin site is not quite as polished as we would like yet, but it's coming).  
  
Here are some highlights of our architecture:  
  

-   _Portal_ - This is a stand-alone Twisted process talking to the outside world. It implements a range of communication protocols, such as telnet (traditional in MUD-world), ssh, ssl, a comet webclient and others. It is an auto-connecting client to _Server_ (below).
-   _Server_ - This is the main MUD server. This twisted server handles everything related to the MUD world. It accesses and updates the database through Django models. It makes the world tick. Since all Players connect to the Server through the Portal's [AMP](http://twistedmatrix.com/documents/8.2.0/api/twisted.protocols.amp.html) connection, it means Server can be restarted without any players getting kicked off the game (they will re-sync from Portal as soon as Server is back up again).
-   _Webserver -_ Evennia optionally starts its own Twisted webserver. This serves the game's website (using the same database as the game for showing game statistics, for example). The website is of course a full Django project, with all the possibilities that entails. The Django _admin site_ allows for modifying the database via a graphical interface. 
-   _Webclient -_ There is a stand-alone MUD web client existing in a page on the default website. This uses Twisted to implement a long-polling ("comet") connection to a javascript client. As far as Evennia's concerned, this is just another outgoing protocol served by the Portal.
-   _Other protocols_ - Since it's easy to add new connectivity, Evennia also offers a bunch of other connectivity options, such as relaying in-game channels to _IRC_ and _IMC2_ as well as _RSS_ feeds and some other goodies. 

  

### On the joining of the two

  
An important thing to note about Twisted's asynchronous model is that there is no magic at work here: Each little snippet of code Twisted loops over _is_ blocking. It's just hopefully not blocking long enough for you to notice. So if you were to put _sleep(10)_ in one of those snippets, then congratulations, you just froze the entire server for ten seconds.  
  
Profiling becomes very important here. Evennia's main launcher takes command arguments to run either of its processes under Python's cProfile module. It also offers the ability to connect any number of dummy Players doing all sorts of automated random actions on the server. Such profile data is invaluable to know what is a bottleneck and what is not.  
  
I never found Twisted asynchronous paradigms much harder to understand than other code. But there are sure ways to write stupid blocking code that will come back and bite you. For example, much of  Evennia's workload is spent in the _Server,_ most notably in its _command handler_. This is not so strange; the command handler takes care of parsing and executing all input coming from Players, often modifying the game world in various ways (see my previous post for more info about the command handler).  
The command handler used to be a monolithic, single method. This meant that Twisted had to let it run its full course before letting anyone else do their turn. Using Twisted's _[inlineCallbacks](http://twistedmatrix.com/documents/8.1.0/api/twisted.internet.defer.html#inlineCallbacks)_ instead allowed for yielding at many, many places in this method, giving Twisted ample possibilities to split execution. The effect on multi-user performance was quite impressive. Far from all code can  be rewritten like this though.  
  
Another important bottleneck on asynchronous operations is database operations. Django, as opposed to Twisted, is _not_ an asynchronous framework. Accessing the database _is_ a blocking operation and can be potentially expensive. It was never extremely bad in testing, to be honest. But for large database operations (e.g. many Players) database access was a noticeable effect.  
  
I have read of some people using Twisted's _deferToThread_ to do database writes. The idea sounds reasonable - just offload the operation to another thread and go on your merry way. It did not help us at all though - rather it made things slower. I don't know if this is some sort of overhead (or error) in my test implementation - or an effect of Python just not being ideal with using threading for concurrency (due to the GIL). Either way, certain databases like SQlite3 doesn't support multiple threads very well anyway, and we prefer to keep giving plenty of options with that. So no _deferToThread_ for database writes. I also did a little testing with parallel processes but found that even slower, at least once the number of writes started to pile up (we will offer easy process-pool offloading for other reasons though).  
  
As many have found out before us, caching is king here. There is not so much to do about writes, but at least in our case the database is more often read than written to. Caching data and accessing the cache instead of accessing a field is doing much for performance, sometimes a _lot._ Database access is always going to cost, but it does not dominate the profile. We are now at a point where one of the most expensive single operations a Player (even a Builder) performs during an entire gaming session is the hashing of their password during login. I'd say that's good enough for our use case anyway.  
  
  

### Django + MUD?

  

It's interesting that whereas Twisted is a pretty natural fit for a Python MUD (I have learned that Twisted was in fact first intended for mudding, long ago), many tend to be intrigued and/or surprised about our use of Django. In the end these are only behind-the-scenes details though. The actual game designer using Evennia don't really see any of this. They don't really _need_ to know neither Django nor Twisted to code their own dream MUD. It's possible the combination fits less for some projects than for others. But at least in our case it has just helped us to offer more features faster and with less headaches.