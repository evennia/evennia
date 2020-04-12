# Developer Tutorials
The developer tutorials are split up into several sections. These are certainly not hard
and fast rules that say, "you must be this skilled to enter." Instead, they're grouped around functionality:
if your goal is to do something that's fully supported by Evennia with a few lines of code, those
tutorials will be primarily located in the 'flat API' section. If you try it and decide it's not
good enough, the more advanced sections will walk you through how you can modify parts of Evennia, or
remove them altogether, to get the exact functionality your game requires.

- Learning Python with Evennia
- The Evennia Way
- Changing the way Evennia functions
- The Full Package

|_Protip_|Learning Python with Evennia|
|---|---|
|![JörMUDgandr][logo] | _JörMUDgandr says, "No matter your skill in Python, becoming an Evennia developer will make you better. There's always a level deeper to explore, one more thing you never knew existed that you can master."_ |

## Resources for all developers
- [Glossary](Glossary) - Words that mean things to us but not to you, yet
- [Continuous Integration](Continuous-Integration) - Keeping your 'under construction' code out of your game
- [Debugging Evennia](Debugging)
- [Version Control / Backups](Version-Control)
- [Game System Examples](../index) - Combat and Shops and Mechs, oh my!
- [Unit Tests](Unit-Testing) - Building the 'canaries in the coal mine' that well tell you which three things broke after your latest line of code.

#####Transitioning from other systems
- [Evennia for DIKU Developers](Evennia-for-Diku-Users)
- [Evennia for Roleplaying Sessions](Evennia-for-roleplaying-sessions)
- [Upgrading from Evennia 0.8 -> 0.9 (Porting from Python 2 -> Python 3) ](Python-3)

## Learning Python with Evennia
- [Setting up PyCharm IDE](Setting-up-PyCharm)
- [Learning Python with Evennia](Python-basic-introduction)
- [Learning Python with Evennia - Part 2](Python-basic-tutorial-part-two)
- [Running and Testing Python code](Execute-Python-Code)

##The Evennia Way
- [Using the Evennia flat API](Evennia-API) - 90% of what you need to know is here
- [Batch Processing](../../evennia_core/system/batchcode/Batch-Processors) - Doing a lot of stuff with a little code
- [Deferred and Asynchronous](ASync-Lite) - Doing stuff 'later'

##Changing Evennia's Functionality
- [First Steps](../python/First-Steps-Coding) - How to make things behave differently than the tin says
- [Out of Band](../../evennia_core/system/portal/OOB) - Sending additional data to the client
- [Parsing Command Arguments](Parsing-command-arguments,-theory-and-best-practices) - Transforming what your users type into usable data

##The Full Package
- [Evennia Technical Documentation](TechDocs) - Complete docstring reference for people who know what they're trying to do but don't remember whether a function returns a list or a boolean
- [Evennia Portal and Server](../../evennia_core/system/portal/portal-server-architecture) - A behind-the-scenes look at Evennia
- [New Database Models](New-Models) - Changing the nature of the data store itself
- [Message Path](../../evennia_core/system/portal/Messagepath) - How a .msg() becomes text on the player's screen
- [Developing Custom Protocols](../../evennia_core/system/portal/Custom-Protocols) - When Telnet's just not enough for you.
- [Asynchronous Execution](Async-Heavy) - You'll know when you're ready for async
- [Profiling and Optimization](Profiling) - Gotta go fast. For servers with hundreds of players.

|_Protip_|What to expect when you're building a game|
|---|---|
|![JörMUDgandr][logo] | _JörMUDgandr says, "Debugging is making one change and watching it not compile, then repeating that process. Eventually, you get to where it compiles but doesn't function, then you get to where it functions but doesn't work, and finally you get to where it works but users hate it!"_ |

[logo]: https://raw.githubusercontent.com/evennia/evennia/master/evennia/web/website/static/website/images/evennia_logo.png
