title: Need your help! 

--- 

[![](https://sites.google.com/site/evenniaserver/_/rsrc/1429261373725/old_evennia/demo_color.png)](https://sites.google.com/site/evenniaserver/_/rsrc/1429261373725/old_evennia/demo_color.png)_This for all you developers out there who want to make a game with Evennia but are not sure about what game to make or where to start off._  
  

### We need an example game

One of the main critiques Evennia get from newbies is the lack of an (optional) full game implementation to use as an example and base to build from. So, Evennia needs a full, BSD-licensed example game. I'm talking "diku-like", something you could in principle hook up and allow players into within minutes of installing Evennia. The Tutorial world we already have is a start but it is more of a solo quest, it's not designed to be a full multiplayer game. Whereas Evennia supports other forms of MU* too, the idea is that the systems from a more "code-heavy" MUD could easily be extracted and adopted to a more freeform-style game whereas the reverse is not generally true.  
  
The exact structure of such a game would be up to the person or team taking this on, but it should be making use of Evennia's api and come distributed as a custom game folder (the folder you get with evennia --init). We will set this up as a separate repository under the [Evennia github organisation](https://github.com/evennia) - a spin-off from the main evennia project, and maintained separately.  
  

### We need you!

  
Thing is, while I am (and, I'm sure other Evennia core devs) certainly willing to give considerable help and input on such a project, it's _not_ something I have time to take the _lead_ on myself. So I'm looking for enthusiastic coders who would be willing to step up to both help and _take the lead_ on this; both designing and (especially) coding such an example game. Even if you have your own game in mind for the future, you _still_ need to build most of these systems, so starting with a generic system will still help you towards that final goal - plus you get to be immortalized in the code credits, of course.  

###   
Suggestion for game

Being an example game, it should be well-documented and following good code practices (this is something we can always fix and adjust as we go though). The systems should be designed as stand-alone/modular as possible to make them easy to rip out and re-purpose (you know people will do so anyway). These are the general features I would imagine are needed (they are open to discussion):  

-   Generic fantasy theme (lore is not the focus here, but it can still be made interesting)
-   Character creation module
-   Races (say, 2-3)
-   Classes (say 2-3)
-   Attributes and Skills (based on D&D? Limit number of skills to the minimal set)
-   Rule module for making skill checks, rolls etc (D&D rules?)
-   Combat system (twitch? Turn-based?)
-   Mobs, both friendly and aggressive, with AI
-   Trade with NPC / other players (money system)
-   Quest system
-   Eventual new GM/admin tools as needed
-   Small game world (batch-built) to demonstrate all features (of good quality to show off)
-   More? Less?

### I'm interested!

Great! We are as a first step looking for a driven **lead dev** for this project, a person who has the enthusiasm, coding experience and _drive_ to see the project through and manage it. You will (hopefully) get plenty of collaborators willing to help out but It is my experience that a successful hobby project really needs at least one person taking responsibility to "lead the charge" and having the final say on features: Collaborative development can otherwise easily mean that everyone does their own thing or cannot agree on a common course. This would be a spin-off from the main Evennia project and maintained separately as mentioned above.  
  
Reply to [this thread](https://groups.google.com/forum/#!msg/evennia/48PMDirb7go/w_hZ1mWhH8AJ) if you are willing to participate **_at any level_** to the project, including chipping in with code from your already ongoing development. I don't know if there'd be any "competition" over the lead-dev position but if multiple really enthusiastic and willing devs step forward we'll handle that then.  
  
So get in touch!