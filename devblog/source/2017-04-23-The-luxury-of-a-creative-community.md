copyrights: Image from http://maxpixel.freegreatpicture.com, released as public domain.

---

[![](https://2.bp.blogspot.com/-dZZUpZiYFsY/WP0R1uhmXvI/AAAAAAAAG8M/q9zszXPIP_00n9C-0B6b1IapbEoiRtqgQCLcB/s320/maxpixel.freegreatpicture.com-Silver-Treasure-Gold-Jewels-Costume-Jewelry-Pearls-395994.jpg)](https://2.bp.blogspot.com/-dZZUpZiYFsY/WP0R1uhmXvI/AAAAAAAAG8M/q9zszXPIP_00n9C-0B6b1IapbEoiRtqgQCLcB/s1600/maxpixel.freegreatpicture.com-Silver-Treasure-Gold-Jewels-Costume-Jewelry-Pearls-395994.jpg)

For this blog post I want to focus on the series of very nice pull requests coming in from a growing cadre of contributors over the last few months.  
  
## Contributed goodness  
  
People have put in a lot of good work to boost Evennia, both by improving existing things and by adding new features. Thanks a lot everyone (below is just a small selection)!  

-    Contrib: Turn-based combat system - this is a full, if intentionally bare-bones implementation of a combat system, meant as a template to put in your particular game system into.
-   Contrib: Clothing sytem - a roleplaying mechanic where a character can 'wear' items and have this show in their descriptions. Worn items can also be layered to hide that underneath. Had plenty of opportunities for extensions to a given game.
-   Contrib: An 'event' system is in the works, for allowing privileged builders to add dynamic code to objects that fires when particular events happen. The PR is not yet merged but promises the oft pondered feature of in-game coding without using softcode (and notably also without the security of softcode!). 

-   A lot of PRs, especially from one user, dealt with cleanup and adherence to PEP8 as well as fixing the 'alerts' given by [LGTM](https://lgtm.com/projects/g/evennia/evennia/) on our code (LGTM is by the way a pretty nifty service, they parse the code from the github repo without actually running it and try to find problems. Abiding by their advice results is cleaner code and it also found some actual edge-case bugs here and there not covered by unit tests. The joint effort has brought us down from some 600+ alerts to somewhere around 90 - the remaining ones are alerts which I don't agree with or which are not important enough to spend effort on). 
-   The help mechanics of Evennia were improved by splitting up the default help command into smaller parts, making it easier to inject some changes to your help system without completely replacing the default one. 
-   Evennia's Xterm256 implementation was not correctly including the additional greyscale colors, those were added with new tags **|=a** ... **|=z**.
-   Evennia has the ability to relay data to external services through 'bots'. An example of this is the IRC bot, which is a sort of 'player' that sits in an in-game channel and connects that to a counterpart-bot sitting in a remote IRC channel. It allows for direct game-IRC communication, something enjoyed by people in the Evennia demo for many years now. The way the bot was defined used to be pretty hard-coded though. A crafty contributor changed that though, but incorporating the bot mechanism into Evennia's normal message flow. This allows for adding new types of bots or extending existing ones without having to modify Evennia's core. There is already an alternative IRC bot out there that represents everyone in the IRC room as a room full of people in the MUD. 
-   Evennia's **Attributes** is a database table connected to other objects via a ForeignKey relation. This relation is cached on the object. A user however found that for certain implementations, such as using Attributes for large coordinate systems, _non-matches_ (that is failed Attribute lookups on the object) can also be cached and leads to dramatic speed increases for those particular use cases. A PR followed. You live and learn.
-   Another contributor helped improve the EvEditor (Evennia's VIM-like in-game text editor) by giving it a code-mode for editing Python code in-game with auto-indents and code execution. Jump into the code mode with the command **@py/edit**.
-   Time scheduling is another feature that has been discussed now and then and has now been added through a PR. This means that rather than specifying '_Do this in 400 seconds_' you can say '_do this at 12AM, in-game time_'. The core system works with the real-world time units. If you want 10 hours to a day or two weeks to a month the same contributor also made an optional calendar contrib for that!
-   A new 'whisper' command was added to the Default cmdset. It's an in-game command for whispering to someone in the same room without other people hearing it. This is a nice thing to have considering Evennia is out-of-the-box pretty much offering the features of a 'talker' type of game.
-   Lots of bug fixes big and small!
-   Some **at_*** hooks were added, such as **at_give(giver, getter)**. This allows for finer control of the give process without handling all the logics at the command level. There are others hooks in the works but those will not be added until in Evennia 0.7. 

## About that Evennia 0.7 ...  
  
So while PRs are popping up left and right in master I've been working in the **devel** branch towards what will be the Evennia 0.7 release. The branch is not ready for public consumption and testing yet But tentatively it's about halfway there as I am slowly [progressing through the tickets](https://github.com/evennia/evennia/projects/6). Most of the upcoming features were covered in the previous blog post so I'll leave it at that.  
  
I just want to end by saying that it's a very luxurious (and awesome) feeling for me to see master-branch Evennia expand with lots of new stuff "without me" so to speak. The power of Open Source indeed!  
    