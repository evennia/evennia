# Default Command Syntax


Evennia allows for any command syntax. 

If you like the way DikuMUDs, LPMuds or MOOs handle things, you could emulate that with Evennia. If you are ambitious you could even design a whole new style, perfectly fitting your own dreams of the ideal game. See the [Command](../Components/Commands.md) documentation for how to do this.

We do offer a default however. The default Evennia setup tends to *resemble* [MUX2](https://www.tinymux.org/), and its cousins [PennMUSH](https://www.pennmush.org), [TinyMUSH](https://github.com/TinyMUSH/TinyMUSH/wiki), and [RhostMUSH](http://www.rhostmush.com/): 

```
command[/switches] object [= options]
```

While the reason for this similarity is partly historical, these codebases offer very mature feature sets for administration and building.

Evennia is *not* a MUX system though. It works very differently in many ways. For example, Evennia
deliberately lacks an online softcode language (a policy explained on our [softcode policy page](./Soft-Code.md)). Evennia also does not shy from using its own syntax when deemed appropriate: the
MUX syntax has grown organically over a long time and is, frankly, rather arcane in places.  All in
all the default command syntax should at most be referred to as "MUX-like" or "MUX-inspired".

```{toctree}
:hidden:
Soft-Code
```