copyrights: Image credit: The Smithsonian

---

[![](https://3.bp.blogspot.com/-5Co5uPbwKTQ/XMF-PalVycI/AAAAAAAAKVU/EAtFXY2nqPUyecpTMagdIz1lsQwk55KVwCLcBGAs/s320/2009-2211.jpg)](https://3.bp.blogspot.com/-5Co5uPbwKTQ/XMF-PalVycI/AAAAAAAAKVU/EAtFXY2nqPUyecpTMagdIz1lsQwk55KVwCLcBGAs/s1600/2009-2211.jpg)


In the last few months, development of the upcoming [Evennia](http://www.evennia.com/) 0.9 has been steaming on. Evennia is, as you may know, a Python library for creating text-based multiplayer games (MUDs, MUSH etc).  
But it's not all backend work! There is also some sweet game-jamming going on, I get to that at the end.   
  
  

### Evennia progress towards Python3 

The regular Evennia _develop_ branch is now running completely in Python 3. Since we are using some new features of this Python release, we will be aiming for Python 3.7 as a minimum version once Evennia 0.9 goes stable. We will also use Django 2.1 and likely Twisted 19 - so we'll be pretty much up-to-date on all our main dependencies.  
  
Now, while the release of Evennia 0.9 is still some time away (there are a bunch of regular bug fixes and minor features that I want to get in there too (see the progress [here on the github 0.9 project page](https://github.com/evennia/evennia/projects/8)), it's worth to consider how much work it'll be for you to migrate and if you should wait or jump in right now.  
  
If you are new, I still recommend you use regular _master_ branch Evennia (using Python 2.7). This is for which all wiki articles and documentation online is currently written after all. Once we move to python3, you'll need to convert your code ... but syntactically the two are really not that different and conversion should not be much of an issue.  
  
Not only are there automatic converters for most stuff, you should only need to do one pass to make sure things work and then you'll be done. [This article](https://sebastianraschka.com/Articles/2014_python_2_3_key_diff.html) is pretty old but it serves well to identify the main differences. Later Py3 versions just adds new stuff which you would just not have had access to in Python2.7. Once 0.9 is released, we'll also make guides for how you go about converting existing code (apart from the wealth of info on this topic online).  
   
That said, if you are feeling more adventurous, or _really_ want to use Python3 right away, many of the Evennia developer regulars have been running and testing _develop_ branch for months now. It's overall been a pretty painless transition - as said, py3 is not that different from py2.  
  
However, _develop_ branch has other features beyond the py3 jump. And those are not yet documented in the main docs. So you'll have to contend with that (but asking in chat/forum works of course). However while it works fine for development already, as a matter of principle I _do not_ recommend ever using Evennia's _develop_ branch for a production game - it can change quickly and may occationally be broken. You have been warned!   
  

### Game Jam

We are now a little more than a week into the [Mud Coders Guild](https://mudcoders.com/)'s second yearly [Game Jam](https://itch.io/jam/enterthemud2). This year's theme is "One Room".  
  
I really hope some more Evennia devs jump on this one because Evennia is perfect for this kind of experimental games. This is because Evennia is not imposing a game style on you - while there are default commands you are free to replace or customize the commands, objects and every aspect of your game to be as specific as you want to your game.  
  
For example, I have a small Game Jam contribution in the works, where I very quickly reworked the default Evennia setup to pretty much make it into a different genre of game.  
  
Usually the systems I make for Evennia are generic and intended for any game-type. By contrast, making somehing highly niched is super-fast to do: Building a whole new framework for game mechanisms along with build helpers for me to quickly make content took no more than three days.  
  
There will no doubt be some iteration, but I hope to spend the rest of the jam time on content and gameplay. I have some RL things happening in the coming weeks (including work on Evennia proper) but if I can get the time to tie my jam entry together, I'll likely make one or two blog posts about how it was developed and my reasons for making the choices i did. Most likely the code will appear as an Evennia contribution in case people want to do something similar for their own projects.  
  
So, busy days.