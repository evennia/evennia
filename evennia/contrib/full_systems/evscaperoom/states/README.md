# Room state modules

The Evscaperoom goes through a series of 'states' as the players solve puzzles
and progress towards escaping. The States are managed by the StateHandler. When
a certain set of criteria (different for each state) have been fulfilled, the
state ends by telling the StateHandler what state should be loaded next.

A 'state' is a series of Python instructions in a module. A state could mean
the room description changing or new objects appearing, or flag being set that
changes the behavior of existing objects.

The states are stored in Python modules, with file names on the form
`state_001_<name_of_state>.py`. The numbers help organize the states in the file
system but they don't necessarily need to follow each other in the exact
sequence.

Each state module must make a class `State` available in the global scope. This
should be a child of `evennia.contrib.evscaperoom.state.BaseState`. The
methods on this class will be called to initialize the state and clean up etc.
There are no other restrictions on the module.

The first state (*when the room is created) defaults to being `state_001_start.py`,
this can be changed with `settings.EVSCAPEROOM_STATE_STATE`.
