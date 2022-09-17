title: Project plans and Splitting a Setting in two
copyright: Image from [freeimageslive.co.uk](http://www.freeimageslive.co.uk/free_stock_image/pausebreakkeyjpg), released under CC Attribution 3.0. Image by freeimageslive - stockmedia.cc.

--- 

![Pause/Break button](images/pause_break_key.jpg)

As those following Evennia development should be aware of for now, we are approaching the 1.0 release of Evennia, the MU*-building framework. 

Thing is, that release has been coming 'soon' for quite a while now. Since some time you can already test Evennia 1.0-dev by checking out the  Evennia `develop` branch ([here](https://github.com/evennia/evennia/discussions/2640) for help on how). Evennia 1.0-dev is still changing, but it's already stable enough that It's gotten to the point that people in chat now recommend new users to start fresh with 1.0-dev rather than the 'stable' version 0.9.5, which is now 1.5 years old and is not seeing more updates.  

## Changes to 1.0 release plans

### In short: 
I plan to pause the work on the new beginner tutorial and release 1.0 with that piece of the documentation unfinished. It still has a large swathes of useful info, but the new from-scratch game will not be ready. 

### Longer: 
One of the reasons for 1.0 not being released is that I have been working on a new beginner-tutorial to go with the new system. This involves making a full little MUD game from scratch, and I'm making a full system you can both follow lesson-per-lesson as well as implementing it for those that prefer to pull apart code. 

Writing good code as well as full tutorial lessons is however a big, full-time job (next to my actual real-life full-time job) and thus I expect it will take a good while longer before the new tutorial is done. Worse, in the meantime I can't spend much time resolving the 1.0-dev bugs that has been reported by community testers and also block release. 

So I will map out the remaining pieces of the tutorial with informational "Work in progress" markers, merge what I have, and stop work on it for now. 

I'll continue finishing the tutorial in smaller sub-releases after the main 1.0 release.

### What's left for 1.0-dev 

So, with the main bulk of work (the beginner tutorial) on hold, what's left to do? 

- Cleanup the rest of the docs! There's still much to do there, including removing old tutorials that are now covered in the parts of the beginner-tutorial already finished. Also need to connect all pages and structure the docs better. 
- Get into the bug backlog of Evennia 1.0-dev that people have reported. Also work to merge some outstanding PRs. I'll need to triage issues more, but hopefully I can get some help fixing simpler bugs during October's [Hacktoberfest](https://github.com/evennia/evennia/discussions/2858).


## MULTISESSION_MODE changes (this will affect your current game!)

That said, now to some recent changes in 1.0-dev. This one is important since it affects your existing game. 

### In short: 
The functionality of  `MULTISESSION_MODE` has been broken into smaller sub-settings. This makes it a lot more flexible, but if you used the 'side-effects' of a higher `MULTISESSION_MODE` in your game, you now need to set a few other settings to get that back. 

### Longer: 
The `MULTISESSION_MODE` is a long-standing Evennia setting. It controls how many sessions you can connect to the game at a time. In other words, how many game clients you can open against the same accoung login at the same time. 

- Mode 0: A single session. Connecting a new one will disconnect the previous one.
- Mode 1: Multiple sessions can be connected. When you puppet a Character, each session will see the same output. 
- Mode 2: Multiple sessions can be connected. Each session can puppet one Character each. 
- Mode 3: Multiple sessions can be connected. Multiple sessions can puppet a Character, each session will see the same output.

Thing is that for the longest time, this setting has _also_ controlled other things: 
- Mode 0,1: A Character of the same name as the Account is auto-created when first connecting.
- Mode 0,1: You auto-connect to your last character whenever you log in.
- Mode 2,3: You don't get an auto-created character and end up in and OOC 'character' select screen when logging in. 

These things don't really belong together. For example, if you want players to be able to choose between multiple characters (a character selection screen) but only play one at a time (`MULTISESSION_MODE` 0 or 1), you'd need to work around Evennia's default.

As of today, I've merged a change to Evennia 1.0-dev (`develop` branch) which changes this. 

- `MULTISESSION_MODE` now _only_ controls how sessions connect and how they can puppet characters. 
- `MAX_NR_SIMULTANEOUS_PUPPETS` is a new setting that controls how many puppets you can control for `MULTISESSION_MODE` 2 and 3. This will not change anything for modes 0 and 1 (always acts as 1 due to how those modes work).
- `AUTO_CREATE_CHARACTERS_WITH_ACCOUNT` allows you to turn off the auto-creation of a character with the same name as the Account when you register. This used to be enforced as a part of `MULTISESSION_MODE` 0 or 1.
- `AUTO_PUPPET_ON_LOGIN` controls if you will auto-connect to the last thing you puppet when you login, of if you'll end up OOC (by default at a character selection screen). Again, this used to be enforced by `MULTISESSION_MODE` 0 or 1.
- `MAX_NR_CHARACTERS` existed before. It controls how many characters the default `charcreate` command will allow you to create. 

By default these settings are all setup to mimic the old `MULTISESSION_MODE` 0, so you should not notice any difference in a fresh game. 

The drawback is that if you use a higher `MULTISESSION_MODE` in your existing game, you will need to tweak these settings to get back what you had before. Also, if you overrode `Account` or the default login commands, you may need to tweak things to match the new upstream default. 