# Beginner Tutorial

```{sidebar} Beginner Tutorial Parts
- **[Introduction](./Beginner-Tutorial-Overview.md)**
<br>Getting set up.
- Part 1: [What We Have](Part1/Beginner-Tutorial-Part1-Overview.md)
<br>A tour of Evennia and how to use the tools, including an introduction to Python.
- Part 2: [What We Want](Part2/Beginner-Tutorial-Part2-Overview.md)
<br>Planning our tutorial game and what to consider when planning your own.
- Part 3: [How We Get There](Part3/Beginner-Tutorial-Part3-Overview.md)
<br>Getting down to the meat of extending Evennia to make your game.
- Part 4: [Using What We Created](Part4/Beginner-Tutorial-Part4-Overview.md)
<br>Building a tech-demo and world content to go with our code.
- Part 5: [Showing the World](Part5/Beginner-Tutorial-Part5-Overview.md)
<br>Taking our new game online and letting players try it out.
```

Welcome to Evennia! This multi-part Beginner Tutorial will help get you off the ground and running.

You may choose topics that seem interesting but, if you follow this tutorial through to the end, you will have created your own small online game to play and share with others!

Use the menu on the right to navigate the index of each of the tutorial's parts. Use the [next](Part1/Beginner-Tutorial-Part1-Overview.md) and [previous](../Howtos-Overview.md) links at the top/bottom right of each page to jump between lessons.

## Things You Need

- A command line interface
- A MUD client (or web browser)
- A text-editor/IDE
- Evennia installed and a game-dir initialized

### A Command Line Interface

You need to know how to find the terminal/console in your OS. The Evennia server can be controlled from in-game, but you _will_ realistically need to use the command-line interface to get anywhere. Here are some starters:

- [Online Intro to the Command line for different OS:es](https://tutorial.djangogirls.org/en/intro_to_command_line/)

> Note that the documentation typically uses forward-slashes (`/`) for file system paths. Windows users should convert these to back-slashes (`\`) instead.

### A Fresh Game-Dir?

You should make sure that you have successfully [installed Evennia](../../Setup/Installation.md). If you followed the instructions, you will have already created a game-dir. The documentation will continue to refer to this game-dir as `mygame`, so you may want to re-use it or make a new one specific to this tutorial only -- it's up to you.

If you already have a game-dir and want a new one specific to this tutorial, use the `evennia stop` command to halt the running server. Then, [initialize a new game-dir](../../Setup/Installation.md#initialize-a-new-game) somewhere else (_not_ inside the previous game-dir!).

### A MUD Client

You may already have a preferred MUD client. Check out the [grid of supported clients](../../Setup/Client-Support-Grid.md). Or, if telnet's not your thing, you may also simply use Evennia's web-client in your preferred browser.

Make sure you know how to connect and log in to your locally running Evennia server.

> In this documentation we often interchangeably use the terms 'MUD', 'MU', and 'MU*' to represent all the historically different forms of text-based multiplayer game-styles (i.e., MUD, MUX, MUSH, MUCK, MOO, etc.). Evennia can be used to create any of these game-styles... and more!

### A Text Editor or IDE

You need a text editor application to edit Python source files. Most anything that can edit and output raw text should work (...so not Microsoft Word).

- [Here's a blog post summing up a variety of text editor options](https://www.elegantthemes.com/blog/resources/best-code-editors) - these things don't change much from year to year. Popular choices for Python are PyCharm, VSCode, Atom, Sublime Text, and Notepad++. Evennia is -- to a very large degree -- coded in VIM, but it is not suitable for beginners.

```{important} Use Spaces, Not Tabs
Make sure to configure your text editor so that pressing the 'Tab' key inserts _4 spaces_ rather than a tab-character. Because Python is whitespace-aware, this simple practice will make your life much easier.
```

### Running python commands outside game (optional)

This tutorial will primarily assume you are experimenting with Python through your game client, using the in-game `py` command. But you can also explore Python instructions outside of the game. Run the following from your game dir folder:

    $ evennia shell

```{sidebar}
The `evennia shell` console is convenient for experimenting with Python. But note that if you manipulate database objects from `evennia shell`, those changes will not be visible from inside the game until you reload the server. Similarly changes in-game may not visible to the `evennia shell` console until restarting it. As a guideline, use `evennia shell` for testing things out. Don't use it to change the state of a running game. The beginner tutorial uses the in-game `py` command to avoid confusion.
```
This will open an Evennia/Django aware python shell. You should use this instead of just running vanilla `python` since the latter won't set up Django for you and you won't be able to import `evennia` without a lot of extra setup. For an even nicer experience, it's recommended you install the `ipython` program:

     $ pip install ipython3

The `evennia shell` command will use `ipython` automatically if installed.

---

You should now be ready to move on to the [first part of the Beginner Tutorial](Part1/Beginner-Tutorial-Part1-Overview.md)! (In the future, use the `previous | next` buttons on the top/bottom of the page to progress.)

<details>

<summary>
Click here to see the full index of all parts and lessons of the Beginner-Tutorial.
</summary>

```{toctree}

Part1/Beginner-Tutorial-Part1-Overview
Part2/Beginner-Tutorial-Part2-Overview
Part3/Beginner-Tutorial-Part3-Overview
Part4/Beginner-Tutorial-Part4-Overview
Part5/Beginner-Tutorial-Part5-Overview

```

</details>
