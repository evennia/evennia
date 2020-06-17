# Tutorial NPCs listening


This tutorial shows the implementation of an NPC object that responds to characters speaking in
their location. In this example the NPC parrots what is said, but any actions could be triggered
this way.

It is assumed that you already know how to create custom room and character typeclasses, please see
the [Basic Game tutorial](Tutorial-for-basic-MUSH-like-game) if you haven't already done this.

What we will need is simply a new NPC typeclass that can react when someone speaks.

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
        return "%s said: '%s'" % (from_obj, message)
```

When someone in the room speaks to this NPC, its `msg` method will be called. We will modify the
NPCs `.msg` method to catch says so the NPC can respond.


```python
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
                    self.execute_cmd("say %s" % response)   
    
        # this is needed if anyone ever puppets this NPC - without it you would never
        # get any feedback from the server (not even the results of look)
        super().msg(text=text, from_obj=from_obj, **kwargs) 
```

So if the NPC gets a say and that say is not coming from the NPC itself, it will echo it using the
`at_heard_say` hook. Some things of note in the above example:

- The `text` input can be on many different forms depending on where this `msg` is called from.
Instead of trying to analyze `text` in detail with a range of `if` statements we just assume the
form we want and catch the error if it does not match. This simplifies the code considerably. It's
called 'leap before you look' and is a Python paradigm that may feel unfamiliar if you are used to
other languages. Here we 'swallow' the error silently, which is fine when the code checked is
simple. If not we may want to import `evennia.logger.log_trace` and add `log_trace()` in the
`except` clause.
- We use `execute_cmd` to fire the `say` command back. We could also have called
`self.location.msg_contents`  directly but using the Command makes sure all hooks are called (so
those seeing the NPC's `say` can in turn react if they want).
- Note the comments about `super` at the end. This will trigger the 'default' `msg` (in the parent
class) as well. It's not really necessary as long as no one puppets the NPC (by `@ic <npcname>`) but
it's wise to keep in there since the puppeting player will be totally blind if `msg()` is never
returning anything to them!

Now that's done, let's create an NPC and see what it has to say for itself.

```
@reload
@create/drop Guild Master:npc.Npc
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
combining this with using the Character class gives more direct control over how the NPC will react.
Which way to go depends on the design requirements of your particular game.