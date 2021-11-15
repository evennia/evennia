title: Evennia's open bottlenecks 

--- 

Since Evennia hit beta I have been mostly looking behind the scenes to see what can be cleaned up and not in the core server. One way to do that is to check where the bottlenecks are. Since a few commits, Evennia's runner has additions for launching the Python cProfiler at startup. This can be done for both the Portal and the Server separately.  

I have created a test runner (soon to hit trunk) that launches dummy clients. They log on and then goes about their way executing commands, creating objects and so on. The result of looking at the profiling data (using e.g. _runsnake)_ has been very interesting.  

  

Firstly, a comparably small part of execution time is actually spent in Evennia modules - most is spent using Python built-ins and in the Twisted/Django libraries. This is promising in a way - at least there are no expensive loops in the Evennia code itself that sucks up cycles. Of course it also means we depend heavily on django/twisted (no surprise there) and especially when it comes to database access, I know there could be more caching going on so as to cut down on db calls. 

  

Of the Evennia modules, a lot of time is spent in getting properties off objects - this is hard to avoid, it a side effect of Evennia's typeclass system - and this is cached very aggressively already. What also stands out as taking a considerable time is the command system - the merging of command sets in particular does a lot of comparing operations. This happens every time a command is called, so there are things to be done there. The same goes for the help system; it needs to collect all the currently active command sets for the calling player. Maybe this could be cached somehow.

  

More work on this is needed, but as usual optimization is a double-edged sword. Evennia is written to have a very readable code. Optimization is usually the opposite of readable, so one needs to thread carefully.