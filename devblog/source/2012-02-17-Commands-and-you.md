_Commands_ define how a Player interacts with a given game. In a text-based game it's not amiss to say that the available commands are paramount to the user experience. In principle commands could represent mouse clicks and other modernistic GUI sugar - but for this blog I'll stick with the traditional entered text.  
  
Like most things in Evennia, Commands are Python classes. If you read the [documentation](http://code.google.com/p/evennia/wiki/Commands) about them you'll find that the command classes are clumped together and tacked onto all objects in-game. Commands hanging onto a Character object will be available all the time, whereas commands tacked onto a grandfather's clock will only be available to you when you stand in front of said clock.  
  
The interesting thing with Commands being classes is that each Character gets a separate instance of each command. So when you do _look_ 100 times in a row, it's always the _same_ Look command instance that has its methods called by the engine. Apart from being an efficient way to handle things, this has a major neat side-effect:  

> _You can store things on the Command object and whatever you store can be retrieved next time you execute that command._

  
I find this very cool mainly because I didn't really plan with this in mind when designing the command system - it was a happy side effect. A use I have thought of is to implement cooldowns. Say you have a powerful _bash_ command. It makes a lot of damage, but you need time to recover between bashes. So when you do the _bash_ command the Bash command object simply stores the current time on itself:  

> self.last_bash = time.time()

Next time the Player tries to use _bash_, all the command object needs to is to check if self.last_bash is set, and compare the time stored herein with the current time. No twisted tasks needed, no overhead. Very neat and tidy.  
  
Another nice functionality (just added today in fact) is that Evennia can be set to _store a copy of the last command object executed_. What can one do with this? For starters, it allows for commands to check what a previous command was. This can be useful in itself, but since the next command actually have access to (a copy of) the previous command object itself, it will allow a lot more than that.  
  
Consider a _look_ command that remembers whatever object it is looking at. Since the Look command is a Python object, it simply stores the looked-at object on itself before returning the normal info to the Player. Next, let's assume we use a _get_ command. If no argument is given to this _get_ (no given object to pick up), the _get_ normally returns an error. But it can now instead peek at the _previous_ command (look) and see what _that_ command operated on. This allows for nice potential constructs like  

> >> look [at] box 

> >> get [it]

Evennia does not use this functionality in its default command set, but it offers some very powerful possibilities for MUD creators to design clever parsing schemes.