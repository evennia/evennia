# The action system

The action system allows the players' characters to perform actions that take
a certain amount of time to complete. When the player successfully types a
command that leads to an action, the action is not completed right away, but
takes a certain amount of time to finish. When that time expires, the character
attempts to perform the action. If all the requirements for the action's
success are met, the action succeeds. If not, it fails. Actions can also be
cancelled before their completion. All actions employ body parts, and multiple
actions can be performed at once so long as they do not share the same
bodyparts. Based on their personal settings, characters may add actions to a
personal queue, allowing them to be performed later, when these actions share
body parts with actions that are currently underway.

The action system operates in two modes, able to shift seamlessly from one to
the other. In real-time mode, the amount of time it takes to complete an action,
in real-world seconds, equals the action's duration. In turn-based mode, time
jumps from the moment of completion of one action to the moment of completion
of the next, so that whenever an action is completed, the person who completed
it gets a turn in which they can initiate other actions. If someone does not
act at all during their turn, they get another turn that will take effect as
soon as the last of the currently ongoing actions is completed. Finally, if
someone cancels an action out of their turn, they receive a turn as soon as the
current turn is over. Actions take place in the same order in real-time and
turn-based mode, the order being determined by the times at which the actions
would be completed, with the minor caveat that, as mentioned before, time
progresses at a continuous pace in real-time mode and a "jumping" pace in
turn-based mode.

When turn-based mode starts, each character is assigned a turn action with a
duration of zero, which simply means that the turn action is completed as soon
as it starts. Because each character gets a turn (during which they may start
new actions) whenever one of their actions has been completed, this guarantees
that everyone gets a turn at the start of turn-based mode. Each player
character's turn lasts a minute and can be ended prematurely using the "done"
command, while each NPC's turn lasts five seconds. It is perfectly possible for
the same character to have multiple turns in a row if they perform a series of
very quick actions in succession.

To switch to turn-based mode, PCs and NPCs may turn on their "turnbased"
setting. If at least one character in the room sets their turnbased status to
on, the room shifts to turn-based mode. Once all of the PCs and NPCs have set
their turnbased status to off, the room shifts back to real-time mode. Any
actions that have come closer in time to their completion during turn-based
or real-time mode will retain their progress when switching to the opposite
mode. Note that some actions can be set to trigger turn-based mode, and to do
so, they will activate turn-based mode for both the person carrying them out
and the target of the action (if any).

Movement between rooms is based on two actions, MoveOut and MoveIn. Thus, to
move between two rooms A and B, characters must first move out of room A
towards the exit to room B, and then into room B from the exit back to room A
(if any such exit exists). It takes time to both enter a room and to leave it,
as determined by the character's movement speed and the "distance" attribute
of the rooms' exits. Moving out of a room cancels any actions the character is
performing on targets within the room, as well as any actions being performed
on the character by other characters within the room.

For movement to work properly, there must be at most one exit from a given room
A to another room B. If this is not the case, the distance used to measure the
time required to move into A from B will be the smallest distance among all
these exits. Furthermore, if there is no exit back from room A to room B at all,
the time required to move into A from B will be the same as the time required
to move out of B towards A.

## Hooking up the action system

The action contrib stores its files in its own python package. For convenience,
all the classes and functions that the end-user will need are referenced in the
package's \_\_init\_\_.py file, so that one can import them directly:

```python
from evennia.contrib.actions import *<feature>*
```

To use the action system, the characters, rooms and exits in your game must be
subclassed from ActionCharacter, ActionRoom and ActionExit respectively. Simply
put the following lines in the appropriate files:

```python
from evennia.contrib.actions import ActionCharacter

from evennia.contrib.actions import ActionRoom

from evennia.contrib.actions import ActionExit
```

And then subclass the appropriate 
[typeclasses](https://github.com/evennia/evennia/wiki/Typeclasses "typeclasses"):
subclass your Character class from ActionCharacter, your Room class from
ActionRoom and your Exit class from ActionExit. Then import ActionCmdSet
and ActionDebugCmdSet like so:

```python
from evennia.contrib.actions import ActionCmdSet

from evennia.contrib.actions import ActionDebugCmdSet
``` 
Add these into your game's command sets. That's it: you can now test the
action system using its debug actions.

For a more in-depth description of the process of setting up the action
system, as well as additional steps required to customize the system and
create your own actions (all of which will be essential), read below. 

Each of the ActionCharacter and ActionRoom objects has a handler called
"actions" that stores all methods and properties related to the action
system. When the object is initialized, its actions.setup() method runs,
loading the default parameters for the object. Likewise, running setup()
from the evennia.contrib.actions modulecalls the actions.setup() methods
for all objects that are subclassed from either ActionCharacter or
ActionRoom.

In any subclass you make for the ActionCharacter and ActionRoom classes,
you must be sure to fill in several members of the "actions" handler for
the object being created, as well as call
[super](https://docs.python.org/2/library/functions.html#super
"the super function"), within at_object_creation. 

For subclasses of __ActionCharacter__, you should do:

```python
at_object_creation(self):
    self.actions.movespeed = <your function here>
    self.actions.movetype = <your string here>
    self.actions.bodypart_movement_map = <your function here>
   *[...]*
    super(ActionCharacter, self).at_object_creation()
```

The movement speed (movespeed) function has a single argument, a reference to
the character object itself. It must return a floating-point value in distance
units per second. Distance units are the units of measurement assigned to exits
to determine how far one must travel to get from the middle of the room to the
exit, or conversely from the exit to the middle of the room. At the bare
minimum, a simple movespeed function can simply return a floating-point value
that represents the character's permanent movement speed. More complex
movespeed functions can invoke the character object's action.movetype attribute
and pick a given movement speed based on the movement type being used, as well
as other factors such as the character's agility.

To have characters set their movement type during the game, such as through a
"pace" command, ensure that the command does the following:

```python
    <character object>.actions.movetype = <your string here>
```

It is not necessary to include either movespeed or movetype. When you fail to
include movespeed or movetype, the movement speed of the character will default
to 1 distance unit per second. If, furthermore, the exit that the character
chooses to traverse has a distance value of 1, then it will take 1 second to
traverse it. Thus, you usually want to set the exits' distance values or give
the characters movespeed functions, or both.

The bodypart_movement_map function also has a single argument, a string
representing the movement type being performed. You will want this string to
be one you would assign to self.actions.movetype. The bodypart_movement_map
function returns a string of comma-separated bodypart names, the same as you
would find in an action's "bodyparts" item. While it is not necessary to set
this function, the consequence of not doing so is that all movement actions
will use no bodyparts at all, meaning that characters could issue a vast number
of concurrent movement actions, as well as start moving to an exit immediately
upon entering a room, rather than as soon as their MoveIn action was completed.

You can also create a method for your character class called
*pre_process_action* and one called *post_process_action*, which the action
system calls just before and just after the action is completed.
pre_process_action must receive a single argument, the dictionary of the action
being performed, while post_process_action receives two arguments, the
dictionary of the action being performed as well as a boolean set to True when
the action succeeds, and to False when it fails.

When you subclass from __ActionRoom__, you should do: 

```python
at_object_creation(self)
    self.actions.view = <your function here>
   *[...]*
    super(ActionRoom, self).at_object_creation()
```

The view function must have two arguments. The first of these is the object
that is being viewed and the second is the character viewing it. It will return
either a formatted string or the value False, the former when the object being
viewed can be seen by the viewer, and the latter when the object being viewed
is invisible to the viewer. The string can contain the name of the object being
viewed, its description or anything else the coder desires. The view function
is used automatically inside the ActionRoom's "actions.display" method and
should never need to be caled directly.

Finally, when you subclass from __ActionExit__, you should do:
```python
at_object_creation(self)
    self.distance = <your float here>
   *[...]*
    super(ActionExit, self).at_object_creation()
```

The distance value of an exit represents how far one must travel to move into
the room from the exit, and to move from the room to the exit. It is used in
measuring travel times, together with the character's movement speed.

The action system comes with two sets of
__[commands](https://github.com/evennia/evennia/wiki/Commands "commands")__,
one for characters and the other for staff. To load them, simply add them to
one of your [CmdSets](https://github.com/evennia/evennia/wiki/Command%20Sets "command sets"),
such as the ones in your game's commands/default_cmdsets.py file:

```python
from evennia.contrib.actions import ActionCmdSet
from evennia.contrib.actions import ActionDebugCmdSet

*[...]*

class CharacterCmdSet(default_cmds.CharacterCmdSet):
*[...]*
    def at_cmdset_creation(self):
*[...]*
        self.add(ActionCmdSet())
     
class PlayerCmdSet(default_cmds.PlayerCmdSet):
*[...]*        
    def at_cmdset_creation(self):
*[...]*
        self.add(ActionDebugCmdSet())
```

The actions module provides two __command sets__. The ActionCmdSet, meant for
characters, provides commands for getting information about actions, changing
settings related to the action system and stopping various actions, while the
ActionDebugCmdSet includes debugging commands for staff. The commands are
listed [below](#commands).
 
Finally, the evennia.contrib.actions module supplies the __Action__ class,
which all the actions you design will inherit. A thorough description of this
class can be found further down this document in its own [section](#actions).
This is how you import the Action class:

```python
from evennia.contrib.actions import Action
```

## The ActionCharacter and ActionRoom classes

The full functionality of the ActionCharacter and ActionRoom classes can be
accessed through a handler found in the class, called "actions". This handler
has several properties that you might sometimes want to change, as well as
methods you will want to call or overload and a few things that you should
set in the at_object_creation method as described in the section above.

ActionCharacter objects have the property ```actions.active```. Switching this
from True to False prohibits the character from performing any actions that do
not have their "passive" value set to True, and cancels all prohibited actions
that are being carried out by the character at present. Switching this from
False to True allows the character to perform actions again and makes them
begin the first of their queued actions immediately, if any such actions exist.
You can use this property to simulate effects such as paralysis and death.

The ActionCharacter's ```actions.done()``` method may be called to have the
character end their turn. This is automatically implemented in the "done"
command (see below).

The ```actions.stop(ongoing=True, queued=False)``` method stops all of the
character's ongoing and/or queued actions, based on the parameters given to it.
The "stop" command automatically implements this method (see below).

Finally, the "actions.unpuppet" command stops all of the character's
cancellable actions and turns their turn-based status off (you should make sure
that non-cancellable actions never have their "invokes_tb" item set to True,
because this would prevent the character from leaving turn-based mode and would
lock the room in turn-based mode). You should probably call this in your
character's at_pre_unpuppet method. 

ActionRoom objects have the method ```actions.display(viewed_object, message,
target=None, data="", default=False)```, which will show everyone in the room
a processed version of the message string in the arguments list according to
the room's view function (if you have set it) or in a default way if no view
function exists. The target should be an object, while the data should be a
string or an object. If default is set to True, and the viewed object is
invisible to a given viewer, the name of the viewed object will be replaced
(with "Someone" if the object is a character or "Something" otherwise) in the
version of the message given to that viewer. If default is setto False, and the
viewed object is invisible to the viewer, the message will not be shown to the
viewer at all. Thus, the display method can be used to implement some features
of stealth. 

ActionRoom objects also have the method ```actions.handle_invalid(action,
error_string)```, which will address actions that:
* Do not have a DefaultCharacter object set as their owner (the error string is "NoOwner ")
* Do not have a DefaultRoom object set as their room (the error string is "NoRoom ")
* Have an owner that is not inside their room (the error string is "OwnerNotInRoom ") 
* Have a target but not a reach (the error string is "NoReach ")
* Do not have a target, despite has_target being set (the error string is "NoTarget ")
* Have a target that is not inside their room (the error string is "TargetNotInRoom ")

The strings of all errors encountered are concatenated and passed to the room's
actions.handle_invalid method, which then notifies the MudInfo channel about
the errors and attempts to clean up the action. If you know what you're doing,
you can overload actions.handle_invalid to process invalid actions in a
different way.


## Actions

To create your own actions, you will want to import the Action class as shown above,
then subclass it. The \_\_init\_\_ function of your subclass will have a call to
[super](https://docs.python.org/2/library/functions.html#super) that will include
some or all of the following keyword arguments:

```python
super(<your class>, self).__init__(
    key=<string>,
    desc=<string>, 
    owner=<ActionCharacter object>,
    room=<ActionRoom object>,
    bodyparts=<string of comma-separated bodyparts>,
    target=<object>,
    reach=<string>,
    data=<anything you like, possibly a string>,
    cancellable=<boolean>,
    invokes_tb=<boolean>,
    non_turn=<boolean>,
    msg_defaults=<boolean>,
    begin_msg=<string>,
    duration=<float>,
    )
```

Except for booleans, all arguments that you do not pass to
Action.\_\_init\_\_ will be filled in with either None or an empty string.

Each action contains a dictionary whose items include but are not limited
to the arguments shown above. A full list of the action dictionary's items
follows:

key (string) - the name of the action

desc (string) - a description of the action, used in messages to the owner
                and room. Include the $t token as a placeholder for the target
                and the $d token as a placeholder for the data if it is a
                string.
                The desc should not end with a period.

owner (Character) - the character that is performing the action

room (Room) - the room where the action is taking place

bodyparts (list/string) - a list of strings that represent the bodyparts
                          employed in performing the action, or a single
                          string if only one bodypart is employed

target (Object) - the target of the action, if any

has_target (boolean) - whether the action has a target. It would be insufficient
                       to simply check if target == None, because sometimes that
                       happens when the target is removed.
                       has_target is set automatically in Action.__init__()

data (various) - any extra data appended to the action, such as a telepathic
                 message that is meant to be sent, an object that is meant to
                 be given or a dict containing extra information about a craft

cancellable (boolean) - whether the action can be cancelled. Some actions,
                        such as falling, happen without the character's intent
                        and so cannot be cancelled. Non-cancellable actions
                        are performed even when the character's actions.active
                        flag is set to False.
                        Defaults to True.

invokes_tb (boolean) - whether the action causes the room to switch to 
                       turn-based mode
                       Defaults to False.

non_turn (boolean) - whether the action can be performed outside of the owner's
                     turn
                     Defaults to False

msg_defaults (boolean) - whether to show the default messages for beginning, 
                         completing, failing or canceling the action. Set this
                         to False if you want to put your own messages in
                         at_completion, at_failure and at_cancel, as well as
                         your own custom begin_msg (see below).
                         Defaults to False

begin_msg (string) - The message that will be displayed when the action is  
                     initiated if msg_defaults is set to True. The message
                     can contain the same formatting as the action's desc.
                     If set to the empty string, no message will be shown at
		     all.

onset (float) - the time at which the action began

duration (float) - the time between the action's onset and the action's endtime

endtime (float) - the time at which the action will be completed

reach (string or value) - the reach of the action, reflecting the maximum
                          physical distance that the action can cross. Actions
                          that provide a target should also supply a reach.

at_creation (function) - to be called when the action is created. Takes the
                         action itself as its argument.

at_attempt (function) - to be called at the action's endtime, when the
                        action is attempted, just before its completion.
                        Returns a boolean that is checked against to
                        determine whether the action succeeds or fails.
                        Takes the action itself as its argument.    

at_completion (function) - to be called when the action has been attempted and
                           has succeeded. Takes the action itself as its
                           argument.

at_failure (function) - to be called when the action has been attempted and
                        has failed. Takes the action itself as its argument.

at_cancel (function) - to be called when the action has been cancelled. Takes
                       the action itself as its argument.

You must supply at least a key, a desc, an owner and a room. The key and desc
can sit in the class definition, but the owner and the room must be unique to
each instance of your class. Some desc examples include "performing an action",
"eating $t" and "giving $d to $t". They should generally be of this form, i.e.
with a verb in "ing" form somewhere at the start of the desc.

Each action employs bodyparts, and the same character cannot perform two given
actions at once when they use the same bodyparts. These can include actual
bodyparts such as "torso" and "left arm", as well as more abstract concepts,
such as "movement action" or "combat action" that are meant to group actions
together. Each bodypart is simply a string, and can be cross-referenced with
any body part objects or containers that might be attached to your character.
Beyond serving as a means to keep certain actions from happening at once, you
can associate them with movement types.

If you intend to eschew using bodyparts altogether, you should still supply
actions with a single bodypart, possibly called "body" or "action" (the name
will show up in a few messages to the characters, so do not call it something
silly), because when an action has no bodyparts, any number of copies of it
can be initiated by the same character at a given time. You do not want this
to happen, especially when it comes to combat-related actions.

To have a functional action, you must supply your subclass of Action with some
or all of the at_creation, at_attempt, at_completion, at_failure and at_cancel
methods. These will overload the methods in the Action class. at_creation,
at_completion, at_failure and at_cancel should always call
[super](https://docs.python.org/2/library/functions.html#super), unless you
intend to re-implement some of the base functionality of the action system
itself. at_attempt simply returns True by default, meaning that the action
always succeeds, and thus at_attempt can be safely overriden.

To create an action and initialize it, simply create an object of your subclass
of Action. Say you have a class MyAction that inherits from Action; then simply
do MyAction(owner, room, target, etc). As long as the original at_creation
method of the Action class is called (whether directly or through super), your
action will be properly processed so that it will show up either in the list of
ongoing actions in the room or in the owner's actions queue.


## Commands

There are two command sets in the evennia.contrib.actions module, ActionCmdSet
and ActionDebugCmdSet. The commands in ActionCmdSet are meant for all characters
and include the following:

turnbased - can be used to toggle your character's turn-based status on and off.
Whenever anyone's turn-based status is set to "on" in the room, the room is in
turn-based mode.

actsettings - change various settings pertaining to your character's use of
the action system.

actions - shows a list of all the actions that your character can see
within the room.

stop - stops either the actions in your character's action queue, your
character's ongoing actions, or both.

done - ends your character's turn

queue - shows a list of all the actions in your character's action queue

The commands in the ActionDebugCmdSet are meant for wizards, immortals and
the superuser, and include the following:

@@actslow - performs an action with no bodyparts over 30 seconds

@@actfast - performs an action with no bodyparts over 10 seconds

@@actlarm - performs an action with the 'left arm' bodypart over 20 seconds

@@actlarm - performs an action with the 'right arm' bodypart over 20 seconds

@@actfriend - performs an action towards the target, does not invoke turn-based
mode

@@actfoe - performs an action towards the target, invokes turn-based mode

@@actsetup - calls evennia.contrib.actions.setup(). If you specify the argument
"over", the override flag will be on.

@@debugmsg - enables / disables debug messages pertaining to the action system


## Limitations of the system

* For the time being, only one object may be the target of a given action.
* The various messages sent to the players regarding actions that are being
performed all require the action performer's name to be present at the start
of the message, rather than in the middle of it.
* In turn-based mode, PCs get 60 seconds to complete their turn, while NPCs
get 5. There is no way to customize this at present.
* It is possible to spam-walk by switching to turn-based mode, selecting a
movement target and using the "done" command. The best solution to this is to
subclass the "done" command and have the new class give a failure message if
it is turn-based mode and the character has just input a movement action 
(i.e. the action is in the room's actions.actions.acted list), or if the
character is currently performing a movement action (i.e. if the action is in
the room's actions.actions.list list).

All of these issues can be resolved, and will be resolved if people who are
planning to use the system contact the maintainer, Andrei Pambuccian, about
them. My github name is andrei-pmbcn.

Other limitations that are unlikely to be resolved include the following:

* There should be at most one exit pointing to a given room B in any room A if
B also has an exit to A. If two exits in A point to the same room B, which has
an exit to A, then when moving into A after having left B, the distance used to
calculate the movement speed will be the smallest of the distances of all exits
from A to B. Confused? Just remember that when two rooms have more than one
exit to each other, and the distances of these exits are different, the action
system will pick the smallest of these distances, which may be the wrong one.
* Actions must have at least one body part to ensure that an infinite number of
instances of a given action cannot be created at the same time. Also, certain
messages make use of the body part(s) involved in the action.
* Actions cannot take place between multiple rooms. For instance, you cannot
shoot an arrow from one room to another using the actions system. This is
because time does not flow at the same pace in the two rooms unless they are
both in real-time mode. Imagine a situation wherein you are trying to shoot an
arrow two rooms away, and the room between you and your target is in turn-based
mode! The arrow could be stuck in that room for a minute or more while someone's
turn were taking place.
* If you intend to subclass MoveOut or MoveIn, your subclassed actions should
still have the keys "moveout" and "movein", because if they don't, there will
be errors on attempting to perform MoveOut actions that are queued together.

