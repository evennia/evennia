title: Dummies doing (even more) dummy things

---

[![](https://lh6.googleusercontent.com/proxy/7O-DqSxlUJDFdfWHuOcVzoSro_bzD9BSAipHXLKNG3gpwyTEptGPTOk5MAgX6yjrkAC2r7P1o9YtCZ1cjzTriLrE9I4kL3frKu4ZcvBpp3Uy8CvM4A=s0-d)](http://www.smiley-faces.org/backgrounds/smiley-background-012.jpg)

This is a follow-up to the [Dummies doing dummy things](http://evennia.blogspot.se/2012/02/dummies-doing-dummy-things.html) post. I originally posted info about this update on the mailing list some time back, but it has been pointed out to me that it might be a nice thing to put on the dev blog too since it's well, related to development!  
  
I have been at it with further profiling in Evennia. Notably even more aggressive on-demand caching of objects as well as on-object attributes. I found from profiling that there was an issue with how object access checks were done - they caused the lock handler to hit the database every lock check as it retrieved the needed attributes.  
  
Whereas this was not much of a hit per call, access checks are done _all the time_, for commands, objects, scripts, well everything that might need restricted access.  
After caching also attributes, there is no need to hit the database as often. Some commands, such as listing all command help entries do see this effect (although you still probably wouldn't notice it unless you checked before and after like I did). More importantly, under the hood I'm happy to see that the profile for normal Evennia usage is no longer dominated by Django db calls but by the functional python code in each command - that is, in code that the end user have full control over anyway. I'd say this is a good state of affairs for a mud creation system.  
  
   
In the previous "Dummies ..." post I ran tests with rather extreme conditions - I had dummy clients logging to basically act like heavy builders.  They dug rooms, created and defined objects randomly every five seconds (as well as walking around, reading help files, examining objects and other spurious things). In that post I found that my puny laptop could handle about **75** to **100** such builders at a time without me seeing a slowdown when playing. My old but more powerful desktop could handle some **200** or so.  
  
Now, I didn't re-run these build-heavy tests with the new caches in place. I imagine the numbers will improve a bit, but it's just a guess. By all means, if you expect regularly having more than 100 builders on your game continuously creating 250 new rooms/objects per minute, do get back to me ...  
  
... Instead I ran similar tests with more "normal" client usage. That is, I connected dummy clients that do what most players would do - they walk around, look at stuff, read help files and so on. I connected clients in batches of 100 at a time, letting them create accounts and logging in fully before connecting the next set of 100.  
  
All in all I added **1000** dummy clients this way before I saw a noticeable lag on my small laptop. I didn't find it necessary to try the desktop at this point. Whereas this of course was with a vanilla Evennia install, I'd say it should be reasonable room for most realistic mud concepts to grow in.  
  
With the rather extensive caching going on, it is interesting to know what the memory consumption is.  
 [![](https://4.bp.blogspot.com/-ZNiU4qTi8XE/T8aMHbBck7I/AAAAAAAABRc/vn6EUwkJjJQ/s400/2012-05-01-Evennia_1000_dummies.png)](https://4.bp.blogspot.com/-ZNiU4qTi8XE/T8aMHbBck7I/AAAAAAAABRc/vn6EUwkJjJQ/s1600/2012-05-01-Evennia_1000_dummies.png)  
This graph shows memory info I noted down after adding each block of 100 players. The numbers fluctuated up and down a bit between readings (especially what the OS reported as total usage), which is why the lines are not perfectly straight.  
  
In the end the database holds 1000 players (which also means there are 1000 Character objects), about as many rooms and about twice as many attributes.  The "idmapper cache" is the mapper that makes sure all Django model instances retain their references between accesses (as opposed to normal Django were you can never be sure of this). "Attribute cache" is a cache storing the attribute objects themselves on the Objects, to avoid an extra database lookup. All in all we see that keeping the entire database in memory takes about 450MB.  
  
Evennia's caching is on-demand (so e.g. a room would not be loaded/cached until someone actually accessed it somehow). One could in principle run a script to clean all cached regularly if one was short on RAM - time will tell if this is something any user needs to worry about on modern hardware.