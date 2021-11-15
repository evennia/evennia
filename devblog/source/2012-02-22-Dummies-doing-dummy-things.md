[![](https://4.bp.blogspot.com/-fGC9QysIL-0/T0UwdxCwDiI/AAAAAAAABN4/cklfv7W28Iw/s1600/224108172066smileys.jpg)](https://4.bp.blogspot.com/-fGC9QysIL-0/T0UwdxCwDiI/AAAAAAAABN4/cklfv7W28Iw/s1600/224108172066smileys.jpg)It can often be interesting to test hypothetical situations. So the other day I did a little stress test to see how Evennia handles many players. This is a follow-up to the [open bottlenecks](http://evennia.blogspot.com/2012/02/evennias-open-bottlenecks.html) post.  
  
Evennia, being based on Twisted, is an asynchronous mud server. This means that the program is not multi-threaded but instead it tries to divide up the code it runs into smaller parts. It then quickly switches between executing these parts in turn, giving the impression of doing many things at the same time. There is nothing magical about this - each little piece of code blocks the queue as it runs. So if a particular part takes too long, everyone else will have to wait for their turn. Likewise, if Twisted cannot flip through the queue as fast or faster than new things get added to it, it will start to fall behind.  
  
The good thing is that all code in the queue _will_ run, although if the event loop cannot keep up there will be a noticeable delay before it does. In a mud, this results in "lagging" (in addition to whatever lag is introduced by your network connection). Running Evennia with a handful of users shows no effect of this, but what happens when we start to add more and more players?  
  
My "dummy runner" is a stand alone Twisted program that opens any number of Telnet connections to the Evennia server. Each such "dummy" client is meant to represent a player connecting. In order to mimic actual usage, a dummy client can perform a range of actions:  

-   They can create a new account and log in
-   They can look around and read random help files
-   They can create objects, name and describe them (for testing, the server is set to grant build privileges to all new players)
-   They can examine objects, rooms and themselves 
-   They can dig new rooms, naming all exits and giving aliases
-   They can move between rooms

The clients tick every 5 seconds, at which time there is a 10% chance each will perform an action from the list above (login first, then one of the others at random).  This is meant to spread out the usage a bit, like it would be with real people. Some of these actions actually consist of multiple commands sent to the server (create + describe + set etc), possibly simulating people using shortcuts in their client to send several commands at the same time.  
  
Results  
  
Note that I didn't do a proper objective benchmark. Rather, I logged in and ran commands to see, very subjectively, how the game "felt" with a number of different players. The lag times are rough estimates by putting time() printouts in the server.  
  
First I tried with my development laptop, a Thinkpad X61s. It's about 5 years old by now and certainly not the fastest thing out there, mainly it's small and thin and has great battery life. I used a MySQL database.  

-   **1-50** dummy players didn't show any real difference from playing alone. It's not so strange; 50 players meant on average 5 of them would do an action every 5 seconds. My laptop could handle that just fine.
-   **50-75** dummy players introduced a brief lag (less than a second) when they logged in. 5-7 players logging in at exactly the same time will after all mean a lot of commands sent to the server (they not only log in, they create a new character at the same time). Throughout these tests, clients logging in showed the greatest effect on lag. I think this is mostly an artifact of how the clients operate by sending all relevant login commands at the same time. Once all were logged in, only brief lag occurred at random times as coincidence had all clients do something expensive at the same time.
-   **75-100** dummy players introduced longer lags during login, as on average 7-10 clients were now logging in at exactly the same time. Most commands were unaffected, but occasionally there were some noticeable "hiccups" of about a second depending on what the clients were doing.
-   **100-150** dummy players - here things started to go downhill rapidly. Dummy client login caused seriously lagging and at 150 logged in players, there were 15 exactly simultaneous actions coming in. This was clearly too much for my laptop; it lead to a very varying lag of 1-10 seconds also for simple commands.

Next I tried my desktop machine. This is also not bleeding edge; it's a 4-year old machine with 3GHz processor and 4GB RAM. Since I don't have MySQL on this machine, I used SQLite3, which is interesting in its own right since it's Evennia's default database.  

-   **1-75** dummy players didn't affect the feel of the game one bit.
-   **75-100** showed some occasional effects starting to appear during dummy client logins. 
-   **100-150** dummy players didn't introduce more than a few hiccups of less than a second when approximately 15 clients decided to do something expensive at the same time.
-   **150-200** introduces 2-3 seconds lag during client mass-logins, but once all clients had connected, things worked nicely with only brief random hiccups.
-   **200-250** showed the lag getting more uneven, varying from no lag at all to 2-3 seconds for normal times and up to 5 seconds when clients were logging in.
-   **250-300** dummy players showed login lag getting worse. The general lag varied from 0-5 seconds depending on what the other clients were up to.
-   **300-350** dummy players, about double of what the laptop could handle,  the CPU was not able to keep up anymore. The system remained stable and all commands got executed - eventually. But the lag times went up very rapidly.

Conclusions  
  
So, based on this I would say 50-75 was a comfortable maximum number of (dummy) players to have on my laptop whereas the desktop could handle around 150 without much effort, maybe up to 250 on a good day.  
  
So what does these numbers mean? Well, the dummy clients are rather extreme, and 100+ builders walking around building stuff every 5 seconds is not something one will see in a game. Also so many logging on at the same time is not very likely (although it could happen after a crash or similar). If anything the usage pattern of human players will be more random and spread out, which helps the server to catch up on its event queue.  
  
On the other hand these tests were run with a vanilla Evennia install - a full game might introduce more expensive commands and subsystems. Human players may also introduce random spikes of usage. So take this for what it is - a most subjective, un-scientific and back-of-the-envelope measure.  
  
All in all though, I would say that few MUDs these days see 30 concurrent online users, even less 100 ...