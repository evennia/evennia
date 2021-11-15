[![Jester smiling oh so sweetly](https://1.bp.blogspot.com/-qQX6D_pjg6s/XOmtdhylulI/AAAAAAAAKik/Jtzv1X6X3qYGFo0fXaoj0P-tiEUGC2j6gCLcBGAs/s320/say__hi__to_mrs_buttons_by_griatch_art_d2jof9b-fullview.jpg "The Jester")](https://www.deviantart.com/griatch-art/art/Say-hi-to-Mrs-Buttons-153984575)

[The Jester, your 'adversary'](https://www.deviantart.com/griatch-art/art/Say-hi-to-Mrs-Buttons-153984575)

[](https://1.bp.blogspot.com/-JVAZ65CrRZ0/XOAWibmcrhI/AAAAAAAAKeg/CxL-ddQ5yKk6NnZIrgD7o8FcAatoNazIgCPcBGAYYCw/s1600/Screenshot%2Bfrom%2B2019-05-17%2B11-38-49.png)

  
This is part two of my post-mortem dev-blog about _Evscaperoom_, the multiplayer, text-based 'escape room' I wrote in Python and [Evennia](http://www.evennia.com/). You can read the [first part of the dev blog here](https://evennia.blogspot.com/2019/05/creating-evscaperoom-part-1.html).  
  
This was a game-jam entry I created in a month for the Mud Coder's guild's [Game Jam](https://itch.io/jam/enterthemud2/rate/422945). The theme was _One Room._ You can play the game for free in your browser or with a traditional MUD client. There are no spoilers in these blog posts. 

_Update: These days you can play the Evscaperoom by logging into the Evennia demo game at [https://demo.evennia.com](https://demo.evennia.com). It's just one of the exits you can get through when you enter._  
  
[The first part](https://evennia.blogspot.com/2019/05/creating-evscaperoom-part-1.html) dealt with the overall game-design aspects. This second, final part will go into details of the code and the systems I built to quickly create all the content. The code referenced here is released under the BSD license and is available [on github](https://github.com/Griatch/evscaperoom).  
  
At the time of this post, players have played _Evscaperoom_ for a little more than a week. At the end I'll share some observations and things I learned along the way.  
  
## Ease of building  
  
Over the one-month game jam, I spent about four days making the game's 'engine' and toolset with Evennia. The rest of the time was spent using those tools to actually create game content (the story, puzzles etc).  
  
An important thing was that I didn't want to do any traditional in-game 'building'. That is - no logging into the game and running various commands to build objects and rooms. This is partly because I wanted rooms to be buildable on-demand, but also because I didn't want my game to only exist in the database but in actual version-controllable python modules.  
  
So all of the Evscaperoom is created in code (notably in the game _states_ discussed below). This made it so that I could add unit tests to quickly find bugs and edge cases. It also made it easy to just clone the full game to an online server, init a database and run Evennia on it in a docker when time came to make it public.  
  
  
## Overall game structure   
  

[![The main Evscaperoom menu, showing the option to create a new room or join one of two existing rooms.](https://1.bp.blogspot.com/-qB8ch7ELOKA/XOmHomllRzI/AAAAAAAAKiU/Y9dnXGPgsF4ke8odCDqCrssVJcWScCPGQCLcBGAs/s320/Screenshot%2Bfrom%2B2019-05-25%2B20-20-17.png "Menu")](https://1.bp.blogspot.com/-qB8ch7ELOKA/XOmHomllRzI/AAAAAAAAKiU/Y9dnXGPgsF4ke8odCDqCrssVJcWScCPGQCLcBGAs/s1600/Screenshot%2Bfrom%2B2019-05-25%2B20-20-17.png)

### Main menu

The game loop is simple: When you log in to the game, you get into a menu where you can create a new room to solve or join an existing one. Quitting a room brings you back to that menu. Quitting again leaves the game entirely. In between, you remain inside a single game location ('room').  
  
To make it easier for people to agree to meet up in a room, i made a little 'fantasy name generator' to make unique random names of the rooms. It felt more thematic than showing room id's. The generator combines phonemes together with some very simple logic. Not all comes out easy-to-pronounce, but the result is at least identifiable, like the Sheru and Uyoha above.  
  
I decided that I should not keep empty rooms around, so whenever a room has no more players in it, it's deleted from the database along with all its content. This means players can't really log off and come back to the same room unless a friend stays behind. I felt it was worth keeping things clean and avoid a growing backlog of empty, unsolved rooms. It is, unfortunately, quite common for players to log in, create a room and then immediately log off.  
  
I distribute _Evscaperoom_ as an Evennia 'game dir'. Once you've installed Evennia you can just clone the evscaperoom repo and start a new multiplayer server with it. While the game dir has some Evennia templates in it by default, Almost all the custom logic for this game is in [the evscaperoom/ folder.](https://github.com/Griatch/evscaperoom/tree/master/evscaperoom) The only other modification I did was to make sure Evennia rerouted new players into the Evscaperoom menu when they connect.  
  
  
### Room class  
  
Since all of the gameplay happens in a single room, it made sense to center all of the data-storage around a new, custom Evennia **Room** class. This "EvscapeRoom" class holds all resources for this room. Evennia makes sure to persist it all to the database for you.  
  
The Evennia API provides a lot of powerful but game-general functions. Since our use-case for this game is very strictly defined, I made a slew of helper functions to cut down on boiler plate and pre-set options I wanted to always use.  
  
For example, I added helper methods both for creating and finding objects in the room. On creation, all objects are tagged with the room's unique hash, meaning that one can be sure to never have any cross-over between rooms (like accidentally finding the object in another room (that of course has the exact same name). Since I also decided to never have more than one object with a given name per room, I could make these methods very simple.  
  
The room class also has helpers for finding all players in the room and for sending messages to them. It also catches players leaving so that eventual on-character variables can be cleaned.  
  
Importantly, the very action of deleting the room will automatically clean all resources tied to it, keeping things tidy.  
  
  
### Commands and Objects  
  

[![This shows a list of all commands useful in the room.](https://1.bp.blogspot.com/-JVAZ65CrRZ0/XOAWibmcrhI/AAAAAAAAKeg/CxL-ddQ5yKk6NnZIrgD7o8FcAatoNazIgCPcBGAYYCw/s320/Screenshot%2Bfrom%2B2019-05-17%2B11-38-49.png "The Help screen")](https://1.bp.blogspot.com/-JVAZ65CrRZ0/XOAWibmcrhI/AAAAAAAAKeg/CxL-ddQ5yKk6NnZIrgD7o8FcAatoNazIgCPcBGAYYCw/s1600/Screenshot%2Bfrom%2B2019-05-17%2B11-38-49.png)

The help screen, show all top-level commands

As discussed in part one of this blog, the Evscaperoom, uses a 'focus' mode: The player must examine/focus on an object first in order to operate or use it.  
  
The basic command syntax is:  

**> command [target]**

The parsing I made actually allows for a more complex syntax, but in the end this was all that was really needed, since the currently 'focused' object does not need to be specified. This is the process of using one object with another:  
  
**> examine key**  

```
~~ key (examining) ~~   
This is a brass key.  
  
(To unlock something with it, use insert into <target>)  
```
  
**> insert into door**  
  
    You unlock the **door** with the **key**!  
  
(the _into_ is optional). Here, we focus on the key. We get the key's description and a hint that you can _insert_ it into things. We then insert it into the door, which is another object in the room. The _insert_ command knows that we are focusing on the key already and that it should look into the room for an object door to use this with.  
  
Technically, these on-object 'actions' (like _insert_ above), are dynamically generated. Here is an example of the key object:  
  
 ```python
class Key(EvscaperoomObject):  
    def at_focus_insert(self, caller, **kwargs):  
        target = kwargs['args']  
        obj = caller.search(obj)  
        if not obj:   
            return   
        if obj.check_flag("can_use_key"):  
            obj.handle_insert(self)  
 ``` 
  
Not shown here is that I made a wrapper for the "no-match" command of Evennia. This command fires when no other commands match. I made this instead analyze the currently 'focused' object to see if it had a method at_focus_<command_name> on it. If so, I inject the supplied arguments into that method as a keyword argument _args_.  
  
So when you focus on the key and give the _insert_ command, the at_focus_insert method on the key will be called with a target to insert the key into_._ We search for the target (the door in the example), check if it even accepts keys and then pass the key to that object to handle. It would then be up to the door to figure out if this particular key unlocks it.  
  
I created a library of base objects that I can just use as mixins for the object I want to create. Here's an example:  

```python
from evscaperoom import objects  
  
class Box(objects.Openable,   
    objects.CodeInput,   
    objects.Movable):  
    # ...  
``` 

This class will offer actions to open, insert a code and move the object around. It will need some more configuration and addition of messages to show etc. But overall, this method-to-command solution ended up being very stable and extremely easy to use to make complex, interactive objects.  
  
  
### Room states  
  
I think of the escape room as going through a series of _states_. A change of state could for example be that the user solved a puzzle to open a secret wall. That wall is now open, making new items and puzzles available. This means room description should change along with new objects being created or old ones deleted.  
  
I chose to represent states as Python modules in a folder. To be a state, each module needs to have a global-level class **State** inheriting from my new **BaseState** class. This class has methods for initializing and cleaning up the state, as well as was for figuring out which state to go to next. As the system initializes the new state, it gets the current room as argument, so it can modify it.  
  
This is a (simplified) example of a state module:   
  
```python
# module `state_001_start.py`  
      
from evscaperoom.state import BaseState  
from evscaperoom import objects  
    
MUG_DESC = """  
A blue mug filled with a swirling liquid.   
On it is written "DRINK ME" with big letters.  
"""  
  
class Mug(objects.EvscapeRoomObject):  
    def at_focus_drink(self, caller, **kwargs):   
        caller.msg(f"You drink {self.key}.")   
        self.next_state() # trigger next state  
  
class State(BaseState):  
  
    hints = ["You are feeling a little thirsty...",  
             "Drink from the mug, dummy."]  
  
    next_state = "state_002_big_puzzle"  
  
    def init(self):   
        mug = self.create_object(  
        Mug, key="wooden mug", aliases=["mug"])  
        mug.db.desc = MUG_DESC.strip()  
```
  
In this simple state, a mug is created, and when you drink from it, the next state is triggered. The base object has a helper function to trigger the next state since I found that interactive with an object is almost always the reason for switching states.  
  
The state-class has a lot of useful properties to set, such as which the next state should be (this can be overridden in case of branching paths). You can also store  
a sequence of hints specific for that state.  
  
  
### Informing the room  
  
I wrote the content in second-person perspective (_"You open the door"_). This is however a multiplayer game and I didn't intially appreciate how many texts must also exist in a third-party form for the rest of the room to see (_"Griatch opens the door"_).  
  
As the amount of text grew (the Evscaperoom has close to 10 000 lines of code, a lot of which is content strings), it became clear that it would not be feasible to manually supply third-persion version strings as well.  
  
The solution was to add parsing and translation of pronouns and verbs (a concept I first saw on the game _Armageddon_).  
  
I write the string like this:  
```  
    OPEN_TEXT = "~You ~open the *door."  
```
The ~ marks text that should be parsed for second/third-person use (I'll discuss the *door marking in the next section). This I then send to a helper method that either sends it only to you (which means it comes back pretty much the same, but without the special markers) or to you _and_ to the room, in which it will look different depending on who receives it:  
  
I see 

    You open the [door].
     
Others see

    Griatch opens the [door]. 
  
English is luckily pretty easy to use for this kind of automatic translation - in general you can just add an "s" to the end of the verb. I made a simple mapping for the few irregular verbs I ended up using.  
  
Overall, this made it quick to present multiple viewpoints with minimal extra text to write.  
  

[![Shows the various accessibility options for showing items.](https://1.bp.blogspot.com/-HdLAfVl8P5A/XOAWjd_zoDI/AAAAAAAAKek/KnWDYcsFZP0w1Fb9DEFTd64BkWmnAgIFACPcBGAYYCw/s320/Screenshot%2Bfrom%2B2019-05-17%2B11-49-20.png "option menu")](https://1.bp.blogspot.com/-HdLAfVl8P5A/XOAWjd_zoDI/AAAAAAAAKek/KnWDYcsFZP0w1Fb9DEFTd64BkWmnAgIFACPcBGAYYCw/s1600/Screenshot%2Bfrom%2B2019-05-17%2B11-49-20.png)

> The option menu

The *door -style marking allowed me to generalize how target-able objects in the room were displayed. This meant that users can customize how objects are shown to them. The default is to mark them both with colors and square brackets (this makes it clear also for people with screen readers). But one can also use only colors or turn off the marking completely (hard mode).  
  
## Bringing it online  
  
Evennia is both a mud framework and mudserver as well as a webserver based on [Twisted](https://twistedmatrix.com/trac/). It runs the game's website (with the help of [Django](https://www.djangoproject.com/)) and also provides its own HTML5 webclient. I tweaked the default website text and played a little with CSS but otherwise didn't spend too much time on this bit.  
  
I got a $5/month DigitalOcean droplet with Ubuntu. I made a new, unprivileged "evennia" user on it and cloned the evscaperoom repo to it. I then started a tmux session and ran the Evennia docker image in there. Getting the game online took maybe thirty minutes, most of which was me figuring out where to open the droplet and DigitalOcean firewalls.  
  
I then pointed [http://experimental.evennia.com](http://experimental.evennia.com/) at the droplet's IP and that was it!  
  
Updating the online server is now only a matter of pushing changes to my github repo, pulling it to the server and reloading Evennia; Before release, I used a private github repo for this, afterwards I simply made it public. Pretty straightforward.  
  
# Some lessons learned  
  
I have gotten pretty positive reviews on Evscaperoom so far. In the first two days people stumbled on some edge-case bugs, but after that it has been very stable. Mostly I've had to make small typos and grammar corrections as I (or players) spot them.   
  
There were nevertheless some things I learned, some of which led to more real improvements post-launch.  
  
## No amount of help is too much help

[![Shows focus on the 'bed', with an example of the header telling how to leave the 'focus' mode.](https://1.bp.blogspot.com/-Qd1rZr-X6So/XOpAV1O5cAI/AAAAAAAAKi0/sTtOwnqnj4Iqf5iEMHOUMhIvTJpEGSEiQCLcBGAs/s320/Screenshot%2Bfrom%2B2019-05-26%2B09-26-49.png "Header example")](https://1.bp.blogspot.com/-Qd1rZr-X6So/XOpAV1O5cAI/AAAAAAAAKi0/sTtOwnqnj4Iqf5iEMHOUMhIvTJpEGSEiQCLcBGAs/s1600/Screenshot%2Bfrom%2B2019-05-26%2B09-26-49.png)

> The header shows how to get out of focus mode

Firstly, the focus-system (examine, then do stuff) is a little un-orthodox and needs to be explained. I saw people logging in, examining exactly _one_ thing and then logging out. Eventually I found out (because a user told me), that this was likely because they could not figure out how to _leave_ the focus mode. They'd just flounder about, think the game was buggy and log off.   
  
The answer (just run _examine_ again) is found with the _help_ command, but clearly this was not intuitive. The solution was to add an explicit help text to the top every time you examine something. After this, the confusion seems to have gone away.   
  
## Make it easy to connect for all tastes
  
Another example - a commenting user had pretty strong opinions about the fact that you used to have to supply a username and password to play the game. They suggested this was a 'huge hurdle'. Not sure if that's true. But unless you want to use a particular name, there is also no actual gameplay _reason_ to formally authenticate for Evscaperoom.   
  
This was easy to fix. Evennia has guest-player support out of the box so I just activated that and supplied some more fantasy-sounding names than the default "Guest 1", "Guest 2" etc. Since then, maybe 40% of players connecting have chosen to do so as an anonymous guest. I don't know if those would have left completely if the option was not available, but it's at least a convenient shortcut for getting into the game.  
  
## Everything takes longer than expected 
  
I already knew this one, but still I fell into the trap of thinking that things were going well and that there would be plenty of time to finish before deadline.   
  
Creating text content is a lot faster than creating graphical assets, but it's still a lot of work. Just the ending 'cinematics' took me almost two days to finish and clean up at the end.   
  
For once I did pick a reasonable scale for this project though. So while the last few days of the Jam was more intense than I would have liked, I never truly felt like I would not be able to finish in time.  
  
  
## Building a MU* game in pure code is awesome  
  
Evennia tries to not instil and specific game type, hence its tools are very general. Wrapping these general tools as a highly opinionated and game-specific toolbox enforced to me just how _easy_ it is to do things when you don't need to cover the general case.  
  
Using the tools and creating content purely in-code was great and ended up leading to a _very_ fast content creation. Python works perfectly as a scripting language and I don't think there is a reason for using in-game building at all for your game, especially not when you are working on your own like this.  
  
I made a few admin-only commands to jump between states and to set flags, but otherwise most bugs were caught by a generic unit test that just looped over all founds states and tried to initialize them, one after another.  
  
  
# Conclusions  
  
For all my work on the Evennia library/server, I've not actually _used_ it for games of my own very much. This was a great opportunity for doing so. It also gave me the opportunity to test the Python3-development branch of Evennia in a production setting.  
  
I found a few edge-case library bugs which I fixed, but overall things worked very smoothly, also for this kind of game which is certainly far away from the normal MU*-mold that most use Evennia for. I am a bit biased, but overall I felt Evennia to be very mature for the use of making a game from scratch.  
  
In the future I will most likely break out the 'engine' and tools of the Evscaperoom into an Evennia contrib so that others can make similar games with it easily.  
  
Looking forward to future game jams now!