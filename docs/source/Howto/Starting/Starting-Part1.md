# Evennia Starting Tutorial

  [Next lesson](Building-Quickstart)
  
This is a multi-part Tutorial that will gradually take you from first installation to making your 
own first little game in Evennia. Let's get started! 

```sidebar:: Parts of the Starting tutorial

  **Part 1**: What we have
    A tour of Evennia and how to use the tools, including an introduction to Python.
  Part 2: `What we want <Starting-Part2>`_
    Planning our tutorial game and what to think about when planning your own in the future.
  Part 3: `How we get there <Starting-Part3>`_ 
       Getting down to the meat of extending Evennia to make our game
  Part 4: `Using what we created <Starting-Part4>`_
    Building a tech-demo and world content to go with our code
  Part 5: `Showing the world <Starting-Part5>`_
    Taking our new game online and let players try it out
```

## Lessons of Part 1 - "What we have"

1. Introduction & Overview (you are here)
1. [Building stuff](Building-Quickstart)
1. [The Tutorial World](Tutorial-World-Introduction)
1. [Python basics](Python-basic-introduction)
1. [Python classes](Python-basic-tutorial-part-two)
1. [Running Python in- and outside the game](Execute-Python-Code)
1. [Understanding errors](Understanding-Errors)
1. [Searching for things](Tutorial-Searching-For-Objects)
1. [A walkthrough of the API](Walkthrough-of-API)

In this first part we'll focus on what we get out of the box in Evennia - we'll get used to the tools,
where things are and how we find things we are looking for. We will also dive into some of things you'll 
need to know to fully utilize the system, including giving a brief rundown of Python concepts. 

## Things you will need 

### A Command line 

First of all, you need to know how to find your Terminal/Console in your OS. The Evennia server can be controlled
from in-game, but you _will_ need to use the command-line to get anywhere. Here are some starters:

- [Django-girls' Intro to the Command line for different OS:es](https://tutorial.djangogirls.org/en/intro_to_command_line/)

### A MUD client

You might already have a MUD-client you prefer. Check out the [grid of supported clients](../../Setup/Client-Support-Grid) for aid. 
If telnet's not your thing, you can also just use Evennia's web client in your browser. 

> In this documentation we often use 'MUD' and 'MU' or 'MU*' interchangeably
  as labels to represent all the historically different forms of text-based multiplayer game-styles, 
  like MUD, MUX, MUSH, MUCK, MOO and others. Evennia can be used to create all those game-styles
  and more.

### An Editor
You need a text-editor to edit Python source files. Most everything that can edit and output raw
text works (so not Word). 

- [Here's a blog post summing up some of the alternatives](https://www.elegantthemes.com/blog/resources/best-code-editors) - these 
things don't change much from year to year. Popular choices for Python are PyCharm, VSCode, Atom, Sublime Text and Notepad++. 
 Evennia is to a very large degree coded in VIM, but that's not suitable for beginners.
 
> Hint: When setting up your editor, make sure that pressing TAB inserts _4 spaces_ rather than a Tab-character. Since
> Python is whitespace-aware, this will make your life a lot easier.


### Set up a game dir for the tutorial

Next you should make sure you have [installed Evennia](../../Setup/Setup-Quickstart). If you followed the instructions
you will already have created a game-dir. You could use that for this tutorial or you may want to do the 
tutorial in its own, isolated game dir; it's up to you.

- If you want a new gamedir for the tutorial game and already have Evennia running with another gamedir, 
first enter that gamedir and run

        evennia stop 
        
> If you want to run two parallel servers, that'd be fine too, but one would have to use 
> different ports from the defaults, or there'd be a clash. We will go into changing settings later.
-  Now go to where you want to create your tutorial-game. We will always refer to it as `mygame` so
  it may be convenient if you do too:
  
        evennia --init mygame
        cd mygame 
        evennia migrate 
        evennia start --log
        
    Add your superuser name and password at the prompt (email is optional). Make sure you can 
    go to `localhost:4000` in your MUD client or to [http://localhost:4001](http://localhost:4001)
    in your web browser (Mac users: Try `127.0.0.1` instead of `localhost` if you have trouble).
  
    The above `--log` flag will have Evennia output all its logs to the terminal. This will block
    the terminal from other input. To leave the log-view, press `Ctrl-C` (`Cmd-C` on Mac). To see
    the log again just run 
    
        evennia --log

  You should now be good to go!  
  
  [Next lesson](Building-Quickstart)
