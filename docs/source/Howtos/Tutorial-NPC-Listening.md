# NPCs that listen to what is said

    > say hi 
    You say, "hi"
    The troll under the bridge answers, "well, well. Hello."

This howto explains how to make an NPC that reacts to characters speaking in their current location. The principle applies to other situations, such as enemies joining a fight or reacting to a character drawing a weapon. 

```python
# mygame/typeclasses/npc.py

from characters import Character

class Npc(Character):
    """
    A NPC typeclass which extends the character class.
    """
    def at_heard_say(self, message, from_obj):
        """
        A simple listener and response. This makes it easy to change for
        subclasses of NPCs reacting differently to says.       

        """ 
        # message will be on the form `<Person> says, "say_text"`
        # we want to get only say_text without the quotes and any spaces
        message = message.split('says, ')[1].strip(' "')

        # we'll make use of this in .msg() below
        return f"{from_obj} said: '{message}'"
```

We add a simple method `at_heard_say` that formats what it hears. We assume that the message that enters it is on the form `Someone says, "Hello"`, and we make sure to only get `Hello` in that example.

We are not actually calling `at_heard_say` yet. We'll handle that next. 

When someone in the room speaks to this NPC, its `msg` method will be called. We will modify the
NPCs `.msg` method to catch says so the NPC can respond.


```{code-block} python
:linenos:
:emphasize-lines:

# mygame/typeclasses/npc.py

from characters import Character
class Npc(Character):

    # [at_heard_say() goes here]

    def msg(self, text=None, from_obj=None, **kwargs):
        "Custom msg() method reacting to say."

        if from_obj != self:
            # make sure to not repeat what we ourselves said or we'll create a loop
            try:
                # if text comes from a say, `text` is `('say_text', {'type': 'say'})`
                say_text, is_say = text[0], text[1]['type'] == 'say'
            except Exception:
                is_say = False
            if is_say:
                # First get the response (if any)
                response = self.at_heard_say(say_text, from_obj)
                # If there is a response
                if response != None:
                    # speak ourselves, using the return
                    self.execute_cmd(f"say {response}")   
    
        # this is needed if anyone ever puppets this NPC - without it you would never
        # get any feedback from the server (not even the results of look)
        super().msg(text=text, from_obj=from_obj, **kwargs) 
```

So if the NPC gets a say and that say is not coming from the NPC itself, it will echo it using the
`at_heard_say` hook. Some things of note in the above example:

- **Line 15** The `text` input can be on many different forms depending on where this `msg` is called from. If you look at the [code of the 'say' command](evennia.commands.default.general.CmdSay) you'd find that it will call `.msg`  with `("Hello", {"type": "say"})`.  We use this knowledge to figure out if this comes from a `say` or not.
- **Line 24**: We use `execute_cmd` to fire the NPCs own `say` command back. This works because the NPC is actually a child of `DefaultCharacter` - so it has the `CharacterCmdSet` on it!  Normally you should use `execute_cmd` only sparingly; it's usually more efficient to call the actual code used by the Command directly. For this tutorial, invoking the command is shorter to write while making sure all hooks are called
- **Line26**: Note the comments about `super` at the end. This will trigger the 'default' `msg` (in the parent class) as well. It's not really necessary as long as no one puppets the NPC (by `@ic <npcname>`) but it's wise to keep in there since the puppeting player will be totally blind if `msg()` is never returning anything to them!

Now that's done, let's create an NPC and see what it has to say for itself.

```
reload
create/drop Guild Master:npc.Npc
```

(you could also give the path as `typeclasses.npc.Npc`, but Evennia will look into the `typeclasses`
folder automatically so this is a little shorter).

    > say hi
    You say, "hi"
    Guild Master says, "Anna said: 'hi'"

## Assorted notes

There are many ways to implement this kind of functionality. An alternative example to overriding
`msg` would be to modify the `at_say` hook on the *Character* instead. It could detect that it's
sending to an NPC and call the `at_heard_say` hook directly.

While the tutorial solution has the advantage of being contained only within the NPC class,
combining this with using the Character class gives more direct control over how the NPC will react. Which way to go depends on the design requirements of your particular game.