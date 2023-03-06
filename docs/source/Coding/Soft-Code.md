# Soft Code


Softcode is a simple programming language that was created for in-game development on TinyMUD derivatives such as MUX, PennMUSH, TinyMUSH, and RhostMUSH. The idea was that by providing a stripped down, minimalistic language for in-game use, you could allow quick and easy building and game development to happen without builders having to learn the 'hardcode' language for those servers (C/C++). There is an added benefit of not having to have to hand out shell access to all developers. Permissions in softcode can be used to alleviate many security problems.

Writing and installing softcode is done through a MUD client. Thus it is not a formatted language. Each softcode function is a single line of varying size. Some functions can be a half of a page long or more which is obviously not very readable nor (easily) maintainable over time.

## Examples of Softcode

Here is a simple 'Hello World!' command:

```bash
    @set me=HELLO_WORLD.C:$hello:@pemit %#=Hello World!
```

 Pasting this into a MUD client, sending it to a MUX/MUSH server and typing 'hello' will theoretically yield 'Hello World!', assuming certain flags are not set on your account object.

Setting attributes in Softcode is done via `@set`. Softcode also allows the use of the ampersand (`&`) symbol. This shorter version looks like this:

```bash
    &HELLO_WORLD.C me=$hello:@pemit %#=Hello World!
```

We could also read the text from an attribute which is retrieved when emitting:

```bash
    &HELLO_VALUE.D me=Hello World
    &HELLO_WORLD.C me=$hello:@pemit %#=[v(HELLO_VALUE.D)]
```

The `v()` function returns the `HELLO_VALUE.D` attribute on the object that the command resides (`me`, which is yourself in this case). This should yield the same output as the first example.

If you are curious about how MUSH/MUX Softcode works, take a look at some external resources:

- https://wiki.tinymux.org/index.php/Softcode
- https://www.duh.com/discordia/mushman/man2x1

## Problems with Softcode

Softcode is excellent at what it was intended for: *simple things*. It is a great tool for making an interactive object, a room with ambiance, simple global commands, simple economies and coded systems.  However, once you start to try to write something like a complex combat system or a higher end economy, you're likely to find yourself buried under a mountain of functions that span multiple objects across your entire code.

Not to mention, softcode is not an inherently fast language. It is not compiled, it is parsed with each calling of a function. While MUX and MUSH parsers have jumped light years ahead of where they once were, they can still stutter under the weight of more complex systems if those are not designed properly.

Also, Softcode is not a standardized language. Different servers each have their own slight variations. Code tools and resources are also limited to the documentation from those servers.

## Changing Times

Now that starting text-based games is easy and an option for even the most technically inarticulate, new projects are a dime a dozen. People are starting new MUDs every day with varying levels of commitment and ability. Because of this shift from fewer, larger, well-staffed games to a bunch of small, one or two developer games, the benefit of softcode fades.

Softcode is great in that it allows a mid to large sized staff all work on the same game without stepping on one another's toes without shell access. However, the rise of modern code collaboration tools (such as private github/gitlab repos) has made it trivial to collaborate on code. 

## Our Solution

Evennia shuns in-game softcode for on-disk Python modules. Python is a popular, mature and professional programming language. Evennia developers have access to the entire library of Python modules out there in the wild - not to mention the vast online help resources available. Python code is not bound to one-line functions on objects; complex systems may be organized neatly into real source code modules, sub-modules, or even broken out into entire Python packages as desired.

So what is *not* included in Evennia is a MUX/MOO-like online player-coding system (aka Softcode).  Advanced coding in Evennia is primarily intended to be done outside the game, in full-fledged Python modules (what MUSH would call 'hardcode'). Advanced building is best handled by extending Evennia's command system with your own sophisticated building commands.

In Evennia you develop your MU like you would any piece of modern software - using your favorite code editor/IDE and online code sharing tools.

## Your Solution
 
Adding advanced and flexible building commands to your game is easy and will probably be enough to satisfy most creative builders. However, if you really, *really* want to offer online coding, there is of course nothing stopping you from adding that to Evennia, no matter our recommendations. You could even re-implement MUX' softcode in Python should you be very ambitious. 

In default Evennia, the [Funcparser](Funcparser) system allows for simple remapping of text on-demand without becomeing a full softcode language. The [contribs](Contrib-Overview) has several tools and utililities to start from when adding more complex in-game building. 