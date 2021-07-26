# Using MUX as a Standard


Evennia allows for any command syntax. If you like the way DikuMUDs, LPMuds or MOOs handle things,
you could emulate that with Evennia. If you are ambitious you could even design a whole new style,
perfectly fitting your own dreams of the ideal game.

We do offer a default however. The default Evennia setup tends to *resemble*
[MUX2](https://www.tinymux.org/), and its cousins [PennMUSH](https://www.pennmush.org),
[TinyMUSH](https://github.com/TinyMUSH/TinyMUSH/wiki), and [RhostMUSH](http://www.rhostmush.com/).
While the reason for this similarity is partly historical, these codebases offer very mature feature
sets for administration and building.

Evennia is *not* a MUX system though. It works very differently in many ways. For example, Evennia
deliberately lacks an online softcode language (a policy explained on our [softcode policy
page](Soft-Code)). Evennia also does not shy from using its own syntax when deemed appropriate: the
MUX syntax has grown organically over a long time and is, frankly, rather arcane in places.  All in
all the default command syntax should at most be referred to as "MUX-like" or "MUX-inspired".

## Documentation policy

All the commands in the default command sets should have their doc-strings formatted on a similar
form:

```python
      """
      Short header
    
      Usage:
        key[/switches, if any] <mandatory args> [optional] choice1||choice2||choice3
    
      Switches:
        switch1    - description
        switch2    - description
    
      Examples:
        usage example and output
    
      Longer documentation detailing the command.
    
      """
```

- Two spaces are used for *indentation* in all default commands. 
- Square brackets `[ ]` surround *optional, skippable arguments*. 
- Angled brackets `< >` surround a _description_ of what to write rather than the exact syntax. 
- *Explicit choices are separated by `|`. To avoid this being parsed as a color code, use `||` (this
will come out as a single `|`) or put spaces around the character ("` | `") if there's plenty of
room.
- The `Switches` and `Examples` blocks are optional based on the Command.  

Here is the `nick` command as an example: 

```python
      """
      Define a personal alias/nick
    
      Usage:
        nick[/switches] <nickname> = [<string>]
        alias             ''
    
      Switches:
        object   - alias an object
        account   - alias an account
        clearall - clear all your aliases
        list     - show all defined aliases (also "nicks" works)
    
      Examples:
        nick hi = say Hello, I'm Sarah!
        nick/object tom = the tall man
    
      A 'nick' is a personal shortcut you create for your own use [...]
    
        """
```

For commands that *require arguments*, the policy is for it to return a `Usage:` string if the
command is entered without any arguments. So for such commands, the Command body should contain
something to the effect of

```python
      if not self.args:
          self.caller.msg("Usage: nick[/switches] <nickname> = [<string>]")
          return
```
