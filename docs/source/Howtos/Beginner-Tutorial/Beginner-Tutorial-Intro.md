# Beginner Tutorial

```{eval-rst}
.. sidebar:: Tutorial Parts

    **Introduction**
      Getting set up.
    Part 1: `What we have <Part1/Beginner-Tutorial-Part1-Intro.html>`_
      A tour of Evennia and how to use the tools, including an introduction to Python.
    Part 2: `What we want <Part2/Beginner-Tutorial-Part2-Intro.html>`_
      Planning our tutorial game and what to think about when planning your own in the future.
    Part 3: `How we get there <Part3/Beginner-Tutorial-Part3-Intro.html>`_
         Getting down to the meat of extending Evennia to make our game
    Part 4: `Using what we created <Part4/Beginner-Tutorial-Part4-Intro.html>`_
      Building a tech-demo and world content to go with our code
    Part 5: `Showing the world <Part5/Beginner-Tutorial-Part5-Intro.html>`_
      Taking our new game online and let players try it out

```
Welcome to Evennia! This multi-part Beginner Tutorial will help you get off the ground. It consists
of five parts, each with several lessons. You can pick what seems interesting, but if you
follow through to the end you will have created a little online game of your own to play
and share with others!

Use the menu on the right to get the index of each tutorial-part. Use the [next](Part1/Beginner-Tutorial-Part1-Intro.md)
and [previous](../Howtos-Overview.md) links to step from lesson to lesson.

## Things you need

- A Command line 
- A MUD client (or web browser)
- A text-editor/IDE
- Evennia installed and a game-dir initialized

### A Command line

You need to know how to find your Terminal/Console in your OS. The Evennia server can be controlled
from in-game, but you _will_ need to use the command-line to get anywhere. Here are some starters:

- [Django-girls' Intro to the Command line for different OS:es](https://tutorial.djangogirls.org/en/intro_to_command_line/)

Note that we usually only show forward-slashes `/` for file system paths. Windows users should mentally convert this to
back-slashes `\` instead.

### A MUD client

You might already have a MUD-client you prefer. Check out the [grid of supported clients](../../Setup/Client-Support-Grid.md) for aid.
If telnet's not your thing, you can also just use Evennia's web client in your browser.

> In this documentation we often use the terms 'MUD', 'MU' or 'MU*' interchangeably
to represent all the historically different forms of text-based multiplayer game-styles,
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

Next you should make sure you have [installed Evennia](../../Setup/Installation.md). If you followed the instructions
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

You should now be good to go on to [the first part of the tutorial](Part1/Beginner-Tutorial-Part1-Intro.md). 
Good luck!

<details>
<summary>
Click here to expand a list of all Beginner-Tutorial sections (all parts).
</summary>

```{toctree}

Part1/Beginner-Tutorial-Part1-Intro
Part2/Beginner-Tutorial-Part2-Intro
Part3/Beginner-Tutorial-Part3-Intro
Part4/Beginner-Tutorial-Part4-Intro
Part5/Beginner-Tutorial-Part5-Intro

```

</details>