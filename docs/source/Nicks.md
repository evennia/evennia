# Nicks


*Nicks*, short for *Nicknames* is a system allowing an object (usually a [Account](./Accounts)) to
assign custom replacement names for other game entities.

Nicks are not to be confused with *Aliases*. Setting an Alias on a game entity actually changes an
inherent attribute on that entity, and everyone in the game will be able to use that alias to
address the entity thereafter. A *Nick* on the other hand, is used to map a different way *you
alone* can refer to that entity. Nicks are also commonly used to replace your input text which means
you can create your own aliases to default commands.

Default Evennia use Nicks in three flavours that determine when Evennia actually tries to do the
substitution.

- inputline - replacement is attempted whenever you write anything on the command line. This is the
default.
- objects - replacement is only attempted when referring to an object
- accounts - replacement is only attempted when referring an account

Here's how to use it in the default command set (using the `nick` command):

     nick ls = look

This is a good one for unix/linux users who are accustomed to using the `ls` command in their daily
life. It is equivalent to `nick/inputline ls = look`.

     nick/object mycar2 = The red sports car

With this example, substitutions will only be done specifically for commands expecting an object
reference, such as

     look mycar2

becomes equivalent to "`look The red sports car`".

     nick/accounts tom = Thomas Johnsson

This is useful for commands searching for accounts explicitly:

     @find *tom

One can use nicks to speed up input. Below we add ourselves a quicker way to build red buttons. In
the future just writing *rb* will be enough to execute that whole long string.

     nick rb = @create button:examples.red_button.RedButton

Nicks could also be used as the start for building a "recog" system suitable for an RP mud.

     nick/account Arnold = The mysterious hooded man

The nick replacer also supports unix-style *templating*:

     nick build $1 $2 = @create/drop $1;$2

This will catch space separated arguments and store them in the the tags `$1` and `$2`, to be
inserted in the replacement string. This example allows you to do `build box crate` and have Evennia
see `@create/drop box;crate`. You may use any `$` numbers between 1 and 99, but the markers must
match between the nick pattern and the replacement.

> If you want to catch "the rest" of a command argument, make sure to put a `$` tag *with no spaces
to the right of it* - it will then receive everything up until the end of the line.

You can also use [shell-type wildcards](http://www.linfo.org/wildcard.html):

- \* - matches everything.
- ? - matches a single character.
- [seq] - matches everything in the sequence, e.g. [xyz] will match both x, y and z
- [!seq] - matches everything *not* in the sequence. e.g. [!xyz] will match all but x,y z.





## Coding with nicks

Nicks are stored as the `Nick` database model and are referred from the normal Evennia
[object](./Objects) through the `nicks` property - this is known as the *NickHandler*. The NickHandler
offers effective error checking, searches and conversion.

```python
    # A command/channel nick:
      obj.nicks.add("greetjack", "tell Jack = Hello pal!")
    
    # An object nick:
      obj.nicks.add("rose", "The red flower", nick_type="object")
    
    # An account nick:
      obj.nicks.add("tom", "Tommy Hill", nick_type="account")
    
    # My own custom nick type (handled by my own game code somehow):
      obj.nicks.add("hood", "The hooded man", nick_type="my_identsystem")
    
    # get back the translated nick:
     full_name = obj.nicks.get("rose", nick_type="object")
    
    # delete a previous set nick
      object.nicks.remove("rose", nick_type="object")
```

In a command definition you can reach the nick handler through `self.caller.nicks`. See the `nick`
command in `evennia/commands/default/general.py` for more examples.

As a last note, The Evennia [channel](./Communications) alias systems are using nicks with the
`nick_type="channel"` in order to allow users to create their own custom aliases to channels.

# Advanced note

Internally, nicks are [Attributes](./Attributes) saved with the `db_attrype` set to "nick" (normal
Attributes has this set to `None`).

The nick stores the replacement data in the Attribute.db_value field as a tuple with four fields
`(regex_nick, template_string, raw_nick, raw_template)`. Here `regex_nick` is the converted regex
representation of the `raw_nick` and the `template-string` is a version of the `raw_template`
prepared for efficient replacement of any `$`- type markers. The `raw_nick` and `raw_template` are
basically the unchanged strings you enter to the `nick` command (with unparsed `$` etc).

If you need to access the tuple for some reason, here's how:

```python
tuple = obj.nicks.get("nickname", return_tuple=True)
# or, alternatively
tuple = obj.nicks.get("nickname", return_obj=True).value
```