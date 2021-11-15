[![](https://4.bp.blogspot.com/-pW3nsIxgroY/WDDFXo3z2dI/AAAAAAAAEs8/n9ehRTZrlggiEIOMGZupSVFxYa7DSGsZgCPcB/s200/evennia_logo_festive_small.png)](https://4.bp.blogspot.com/-pW3nsIxgroY/WDDFXo3z2dI/AAAAAAAAEs8/n9ehRTZrlggiEIOMGZupSVFxYa7DSGsZgCPcB/s1600/evennia_logo_festive_small.png)

So, recently Evennia celebrated its ten-year anniversary. That is, it was on Nov 20, 2006, Greg Taylor made the first repo commit to what would eventually become the Evennia of today. Greg has said that Evennia started out as a "weird experiment" of building a MUD/MUX using Django. The strange name he got from a cheesy NPC in the [Guild Wars](https://wiki.guildwars.com/wiki/Evennia) MMORPG and Greg's [first post](https://groups.google.com/forum/#!category-topic/evennia/evennia-news/5hQTspfWd_Q) to the mailing list also echoes the experimental intention of the codebase. The merger with Twisted came [pretty early too](https://groups.google.com/forum/#!category-topic/evennia/evennia-news/CJ52R4Ws0OM), replacing the early asyncore hack he used and immediately seeing a massive speedup. Evennia got attention from the MUD community - clearly a Python-based MUD system sounded attractive.  
  
When I first joined the project I had been looking at doing something MUD-like in Python for a good while. I had looked over the various existing Python code bases at the time and found them all to be either abandoned or very limited. I had a few week's stunt working with [pymoo](https://sourceforge.net/projects/pymoo/) before asking myself why I was going through the trouble of parsing a custom script language _... in Python_ ... Why not use Python throughout? This is when I came upon Evennia. I started [making contributions](https://groups.google.com/forum/#!category-topic/evennia/evennia-news/yfR0GLKGhJA) and around 2010 I [took over the development](https://groups.google.com/forum/#!category-topic/evennia/evennia-news/zXsA2PaWUoU) as real life commitments forced Greg to step down.  
  
Over the years we have gone through a series of changes. We have gone from using SVN to Mercurial and then to using GIT. We have transited from GoogleCode to GitHub - the main problem of which was converting the wiki documentation (Evennia has [extensive documentation](https://github.com/evennia/evennia/wiki)).  
  
For a long time we used Python's reload() function to add code to the running game. It worked ... sometimes, depending on what you changed. Eventually it turned out to be so unpredictable that we now use two processes, one to connect clients to and the other running the game, meaning we can completely restart one process without disconnecting anyone.  
  
Back in the day you were also expected to create your own game in a folder game/ inside the Evennia repo itself. It made it really hard for us to update that folder without creating merge conflicts all over. Now Evennia is a proper library and the code you write is properly separated from ours.  
  
So in summary, many things have happened over the years, much of it documented in this blog. With 3500 commits, 28 000 lines of code (+46% comments) and some 25 people contributing in the last year, [Openhub](https://www.openhub.net/p/evennia) lists us as  
  

> "_A mature, well-established codebase with a stable commit history, a large development team and very well documented source code_". 

  
It's just words compiled by an algorithm, but they still feel kinda good!  
  
  
While Evennia was always meant to be used for any type of multiplayer text game, this general use have been expanded and cleaned up a lot over the years.  
  
This has been reflected in the width of people wanting to use it for different genres: Over time the MUSH people influenced us into adding the option to play the same character from many different clients at the same time (apparently, playing on the bus and then continuing on another device later is common for such games). Others have wanted to use Evennia for interactive fiction, for hack&slash, deep roleplay, strategy, education or just for learning Python.  
  
Since Evennia is a framework/library and tries to not impose any particular game systems, it means there is much work to do when building a game using Evennia. The result is that there are dozens of games "in production" using Evennia (and more we probably don't know about), but few public releases yet.  
  
The first active "game" may have been an Evennia game/chat supporting the Russian version of 4chan... The community driven Evennia demo-game [Ainneve](http://ainneve.evennia.com/) is also progressing, recently adding combat for testing. This is aimed at offering an example of more game-specific code people can build from (the way Diku does). There are similar projects meant for helping people create RPI (RolePlay Intensive) and MUSH-style games. That said, the Evennia-game [Arx, After the Reckoning](http://games.evennia.com/game/arx) is progressing through beta at a good clip and is showing all signs of becoming the first full-fledged released Evennia game.   
  
  
So cheers, Evennia for turning 10. That's enough of the introspection and history. I'll get back to more technical aspects in the next post.