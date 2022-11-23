# Beginner Tutorial

```{sidebar} Beginner Tutorial Parts
- **[Introduction](./Beginner-Tutorial-Overview.md)**
<br>Getting set up.
- Part 1: [What we have](Part1/Beginner-Tutorial-Part1-Overview.md)
<br>A tour of Evennia and how to use the tools, including an introduction to Python.
- Part 2: [What we want](Part2/Beginner-Tutorial-Part2-Overview.md)
<br>Planning our tutorial game and what to think about when planning your own in the future.
- Part 3: [How we get there](Part3/Beginner-Tutorial-Part3-Overview.md)
<br>Getting down to the meat of extending Evennia to make our game
- Part 4: [Using what we created](Part4/Beginner-Tutorial-Part4-Overview.md)
<br>Building a tech-demo and world content to go with our code
- Part 5: [Showing the world](Part5/Beginner-Tutorial-Part5-Overview.md)
<br>Taking our new game online and let players try it out
```

Welcome to Evennia! This multi-part Beginner Tutorial will help you get off the ground. 

You can pick what seems interesting, but if you follow through to the end you will have created a little online game of your own to play and share with others!

Use the menu on the right to get the index of each tutorial-part. Use the [next](Part1/Beginner-Tutorial-Part1-Overview.md) and [previous](../Howtos-Overview.md) links at the top/bottom right of the page to step between lessons. 

## Things you need

- A Command line 
- A MUD client (or web browser)
- A text-editor/IDE
- Evennia installed and a game-dir initialized

### A Command line

You need to know how to find your Terminal/Console in your OS. The Evennia server can be controlled from in-game, but you _will_ need to use the command-line to get anywhere. Here are some starters:

- [Online Intro to the Command line for different OS:es](https://tutorial.djangogirls.org/en/intro_to_command_line/)

> Note that we usually only show forward-slashes `/` for file system paths. Windows users should mentally convert this to back-slashes `\` instead.

### A MUD client

You might already have a MUD-client you prefer. Check out the [grid of supported clients](../../Setup/Client-Support-Grid.md).
If telnet's not your thing, you can also just use Evennia's web client in your browser.

> In this documentation we often use the terms 'MUD', 'MU' or 'MU*' interchangeably to represent all the historically different forms of text-based multiplayer game-styles, like MUD, MUX, MUSH, MUCK, MOO and others. Evennia can be used to create all those game-styles and more.

### A text Editor or IDE

You need a text-editor to edit Python source files. Most everything that can edit and output raw
text works (so not Word).

- [Here's a blog post summing up some of the alternatives](https://www.elegantthemes.com/blog/resources/best-code-editors) - these things don't change much from year to year. Popular choices for Python are PyCharm, VSCode, Atom, Sublime Text and Notepad++. Evennia is to a very large degree coded in VIM, but that's not suitable for beginners.

```{important} Use spaces, not tabs
```
> Make sure to configure your editor so that pressing TAB inserts _4 spaces_ rather than a Tab-character. Since Python is whitespace-aware, this will make your life a lot easier.

### A fresh game dir?

You should make sure you have [installed Evennia](../../Setup/Installation.md). If you followed the instructions you will already have created a game-dir. 

You could re-use that or make a new one only for this tutorial, it's up to you. 

If you already have a game dir and want a separate one for the tutorial, use `evennia stop` to halt the running server and then [Initialize a new game dir](../../Setup/Installation.md#initialize-a-new-game) somewhere else (_not_ inside the previous game dir!). We refer to it everywhere as `mygame`, so you may want to do the same. 

You should now be ready to move on to the [first lesson](Part1/Beginner-Tutorial-Part1-Overview.md)

<details>
<summary>
Click here to expand a list of all Beginner-Tutorial sections (all parts).
</summary>

```{toctree}

Part1/Beginner-Tutorial-Part1-Overview
Part2/Beginner-Tutorial-Part2-Overview
Part3/Beginner-Tutorial-Part3-Overview
Part4/Beginner-Tutorial-Part4-Overview
Part5/Beginner-Tutorial-Part5-Overview

```

</details>