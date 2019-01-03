
# -*- coding: utf-8 -*-

"""
Evennia batchfile - tutorial_world

Cloud_Keeper 2018 
Adapted from build.ev by Griatch 2011, 2015

This batchfile sets up a starting tutorial area for Evennia.

This uses the custom script parents and code snippets found in the
same folder as this script; Note that we are not using any
modifications of the default player character at all (so you don't
have to change anything in any settings files). We also don't modify
any of the default command functions (except in states). So bear in
mind that the full flexibility of Evennia is not used to its maximum
potential here.

To load this file, load the file as user #1 with

    @batchcode contrib.tutorial_world.build

The area we are building looks like this:

    ? 03,04
    |
+---+----+    +-------------------+    +--------+   +--------+
|        |    |                   |    |gate    |   |corner  |
| cliff  +----+   05 bridge       +----+  09    +---+   11   |
|   02   |    |                   |    |        |   |        |
+---+----+    +---------------+---+    +---+----+   +---+----+
    |    \                    |            |   castle   |
    |     \  +--------+  +----+---+    +---+----+   +---+----+
    |      \ |under-  |  |ledge   |    |wall    |   |court-  |
    |       \|ground  +--+  06    |    |  10    +---+yard    |
    |        |   07   |  |        |    |        |   |   12   |
    |        +--------+  +--------+    +--------+   +---+----+
    |                \                                  |
   ++---------+       \  +--------+    +--------+   +---+----+
   |intro     |        \ |cell    |    |        |   |temple  |
o--+   01     |         \|  08    +----+  trap  |   |   13   |
   |          |          |        |   /|        |   |        |
   +----+-----+          +--------+  / +--+-+-+-+   +---+----+
        |                           /     | | |         |
   +----+-----+          +--------+/   +--+-+-+---------+----+
   |outro     |          |tomb    |    |antechamber          |
o--+   16     +----------+  15    |    |       14            |
   |          |          |        |    |                     |
   +----------+          +--------+    +---------------------+

The numbers mark the order of construction and also the unique alias-ids 
given to each room, to allow safe teleporting and linking between them.

We are going to build this layout using batchcode. Batchcode lets you
use Evennia's API to code your world in full-fledged Python code. We
could have also used batchcommand which is a series of commands your
character would play out in a pre-determined sequence or built our game
manually inside the game.

There are a number of styles when designing your batchcode. One is to
create all the rooms together in a block before addressing each one and
adorning each one with details and exits individually. This is the style
we are going to use in this batchcode script.

As we are designing our game worlds we should be mindful of what commands
we give our players and what information those commands will need. In the 
tutorial world we give our characters the 'look' command to tell players 
about their current location, which uses the obj.db.desc attribute, 
and the 'tutorial' command to give players insider information about the 
features they are seeing, which uses the obj.db.tutorial_info attribute.
Additionally we give players a range of hidden details for them to uncover
using an extended look command, which uses obj.db.details.

***READ AND CLIMB COMMANDS***

When building your own world you might want to separate your world into 
a lot more individual batch files (maybe one for just a few rooms) for easy
handling. 
"""

# We start by importing all the objects and tools we plan to build with
from evennia import create_object
from evennia.contrib import tutorial_world
from evennia.objects import rooms, exits

# Next we create all the rooms in our Tutorial World at the beginning so 
# we can build and connect them in any order.
intro = create_object(tutorial_world.rooms.IntroRoom, key="Introduction")
outro = create_object(tutorial_world.rooms.OutroRoom, key="Leaving Tutorial")
cliff = create_object(tutorial_world.rooms.WeatherRoom, 
                      key="Cliff by the coast", aliases=["cliff", "tut#02"])
osinn = create_object(tutorial_world.rooms.WeatherRoom, 
                      key="Outside Evennia Inn", 
                      aliases=["outside inn", "tut#03"])
evinn = create_object(tutorial_world.rooms.TutorialRoom, 
                      key="The Evennia Inn", 
                      aliases=["evennia inn", "inn", "tut#04"])
bridge = create_object(tutorial_world.rooms.BridgeRoom, 
                       key="The old bridge", 
                       aliases=["bridge", "tut#05"])
ledge = create_object(tutorial_world.rooms.WeatherRoom, 
                      key="Protruding Ledge", 
                      aliases=["cliffledge", "ledge", "tut#06"])
underground = create_object(tutorial_world.rooms.TutorialRoom, 
                            key="Underground passages", 
                            aliases=["passages", "underground", "tut#07"])
cell = create_object(tutorial_world.rooms.DarkRoom, 
                     key="Dark cell",
                     aliases=["dark", "cell", "tut#08"])
gate = create_object(tutorial_world.rooms.TutorialRoom, 
                     key="Ruined gatehouse", 
                     aliases=["gatehouse", "tut#09"])
innerwall = create_object(tutorial_world.rooms.WeatherRoom, 
                          key="Along inner wall", 
                          aliases=["inner wall", "along", "tut#10"])
corner = create_object(tutorial_world.rooms.TutorialRoom, 
                       key="Corner of castle ruins", 
                       aliases=["corner", "tut#11"])
courtyard = create_object(tutorial_world.rooms.WeatherRoom, 
                          key="Overgrown courtyard", 
                          aliases=["courtyard", "tut#12"])
temple = create_object(tutorial_world.rooms.TutorialRoom, 
                       key="The ruined temple", 
                       aliases=["temple", "in", "tut#13"])
antechamber = create_object(tutorial_world.rooms.TutorialRoom, 
                            key="Antechamber", 
                            aliases=["antechamber", "tut#14"])
bird = create_object(tutorial_world.rooms.TeleportRoom, key="Blue bird tomb")
horse = create_object(tutorial_world.rooms.TeleportRoom, 
                      key="Tomb of woman on horse")
crown = create_object(tutorial_world.rooms.TeleportRoom, 
                      key="Tomb of the crowned queen")
shield = create_object(tutorial_world.rooms.TeleportRoom, 
                       key="Tomb of the shield")
hero = create_object(tutorial_world.rooms.TeleportRoom, 
                     key="Tomb of the hero")
tomb = create_object(tutorial_world.rooms.TutorialRoom, 
                     key="Ancient tomb", 
                     aliases=["tut#15"])
exitroom = create_object(tutorial_world.rooms.OutroRoom,
                         key="End of tutorial",
                         aliases=["end", "tut#16"])
                     
# -----------------------------------------------------------------------------
# Entry to the Tutorial World.
#
# This creates an entry into the Tutorial World from where ever the player
# is standing. 'Caller' is a reference to the user of the batchcode cmd.
#
# -----------------------------------------------------------------------------

entry = create_object(exits.Exit, key="Tutorial", aliases=["tut", "intro"], 
                      location=caller.location, destination=intro)

entry.db.desc = ("This starts the |gEvennia tutorial|n, using a small solo "
                 "game to show off some of the server's possibilities.")

# -----------------------------------------------------------------------------
#
# Introduction Room
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
intro.db.desc = ("""
|gWelcome to the Evennia tutorial!|n


The following tutorial consists of a small single-player quest
area. The various rooms are designed to show off some of the power
and possibilities of the Evennia mud creation system. At any time
during this tutorial you can use the |wtutorial|n (or |wtut|n)
command to get some background info about the room or certain objects
to see what is going on "behind the scenes".


To get into the mood of this miniature quest, imagine you are an
adventurer out to find fame and fortune. You have heard rumours of an
old castle ruin by the coast. In its depth a warrior princess was
buried together with her powerful magical weapon - a valuable prize,
if it's true.  Of course this is a chance to adventure that you
cannot turn down!

You reach the coast in the midst of a raging thunderstorm. With wind
and rain screaming in your face you stand where the moor meet the sea
along a high, rocky coast ...


|g(write 'start' or 'begin' to start the tutorial. Try 'tutorial'
to get behind-the-scenes help anywhere.)|n
""")

# Returned by the 'tutorial' command.
intro.attributes.add("tutorial_info", """
You just tried the tutorial command. Use it in various rooms to see
what's technically going on and what you could try in each room. The
intro room assigns some properties to your character, like a simple
"health" property used when fighting. Other rooms and puzzles might do
the same. Leaving the tutorial world through any of the normal exit
rooms will clean away all such temporary properties.

If you play this scenario as superuser, you will see a big red
warning.  This warning is genserated in the intro-rooms Typeclass.
""")

# EXITS
intro_ex1 = create_object(exits.Exit, key="Exit Tutorial", 
                          aliases=["exit", "back"], 
                          location=intro, destination=outro)
intro_ex2 = create_object(exits.Exit, key="Begin Adventure", 
                          aliases=["begin", "start"], 
                          location=intro, destination=cliff)

# -----------------------------------------------------------------------------
#
# Outro Room
# Called from the Intro room; this is a shortcut out of the tutorial. 
# There is another outro room at the end showing more text.
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
outro.db.desc = ("""
You are quitting the Evennia tutorial prematurely! Please come back later.
""")

# Returned by the 'tutorial' command.
intro.attributes.add("tutorial_info", """
This outro room cleans up properties on the character that was set by 
the tutorial.
""")

# EXITS
outro_ex1 = create_object(exits.Exit, key="Start Again", aliases=["start"], 
                          location=outro, destination=intro)

# -----------------------------------------------------------------------------
#
# The Cliff
# This room inherits from a Typeclass called WeatherRoom. It regularly
# and randomly shows some weather effects. Note how we can spread the
# command's arguments over more than one line for easy reading.  we
# also make sure to create plenty of aliases for the room and
# exits. Note the alias tut#02: this unique identifier can be used
# later in the script to always find the way back to this room (for
# example by teleporting and similar). This is necessary since there
# is no way of knowing beforehand what dbref a given room will get in the
# database.
#
# This room has Mood-setting details to look at. This makes use of the custom 
# look command in use on tutorial rooms to display extra text strings. It
# adds the detail as a dictionary Attribute on the room.
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
cliff.db.desc = ("""
You stand on the high coast line overlooking a stormy |wsea|n far
below. Around you the ground is covered in low gray-green grass,
pushed flat by wind and rain. Inland, the vast dark moors begin, only
here and there covered in patches of low trees and brushes.

To the east, you glimpse the ragged outline of a castle |wruin|n. It sits
perched on a sheer cliff out into the water, isolated from the
shore. The only way to reach it seems by way of an old hanging bridge,
anchored not far east from here.
""")

# Details returned by extended 'look' command.
cliff.db.details = {}

desc = """
A fair bit out from the rocky shores you can make out the foggy
outlines of a ruined castle. The once mighty towers have crumbled and
it presents a jagged shape against the rainy sky. The ruin is perched
on its own cliff, only connected to the mainland by means of an old
hanging bridge starting not far east from you.
"""
cliff.db.details["ruin"] = desc
cliff.db.details["ruins"] = desc
cliff.db.details["castle"] = desc

desc = """
The gray sea stretches as far as the eye can see to the east. Far
below you its waves crash against the foot of the cliff. The vast
inland moor meets the ocean along a high and uninviting coastline of
ragged vertical stone.

Once this part of the world might have been beautiful, but now the
eternal winds and storms have washed it all down into a gray and
barren wasteland.
"""
cliff.db.details["sea"] = desc
cliff.db.details["ocean"] = desc
cliff.db.details["waves"] = desc

# Returned by the 'tutorial' command.
intro.attributes.add("tutorial_info", """
Weather room

This room inherits from a parent called WeatherRoom. It uses the
tickerhandler to regularly 'tick and randomly display various
weather-related messages.

The room also has 'details' set on it (such as the ruin in the distance), 
those are snippets of text stored on the room that the custom look command
used for all tutorial rooms can display.
""")

# EXITS

# This exit will lead to a secret area which is unlocked by using a custom
# 'climb' command on the 'gnarled old tree' object we'll create later
cliff_ex1 = create_object(exits.Exit, key="northern path", 
                          aliases=["north", "n", "path"], 
                          location=cliff, destination=osinn)

# We'll hide the exit until they have a tag given by the 'climb' command.
cliff_ex1.locks.add("view:tag(tutorial_climbed_tree, tutorial_world); "
                    "traverse:tag(tutorial_climbed_tree, tutorial_world)")

# Returned by the 'look' command.
cliff_ex1.db.desc = ("""
This is a hardly visible footpath leading off through the rain-beaten
grass. It seems to circle the trees northward. You would never had
noticed it had you not spotted it from up in the tree.
""")

# Returned by the 'tutorial' command.
cliff_ex1.attributes.add("tutorial_info", """
This exit is locked with a lock string that looks like this:

   view:tag(tutorial_climbed_tree, tutorial_world) ; traverse:tag(tutorial_climbed_tree, tutorial_world)

This checks if Character has a Tag named "tutorial_climbed_tree" and
of the category "tutorial_world" set before it allows itself to be
displayed. This Tag is set by the tree object when the 'climb' command
is used.
""")

cliff_ex2 = create_object(exits.Exit, key="old bridge", 
                          aliases=["east", "e", "bridge", "hangbridge"], 
                          location=cliff, destination=bridge)
cliff_ex2.db.desc = ("""
The hanging bridge's foundation sits at the edge of the cliff to the
east - two heavy stone pillars anchor the bridge on this side. The
bridge sways precariously in the storm.
""")

# -----------------------------------------------------------------------------
#
# The Cliff - Old Well
# This is the well you will come back up from if you end up in the underground
#
# -----------------------------------------------------------------------------

cliff_well = create_object(key="Old well", aliases=["well"], location=cliff)

# Returned by 'look' command.
cliff_well.db.desc = ("""
The ruins of an old well sit some way off the path. The stone circle
has collapsed and whereas there is still a chain hanging down the
hole, it does not look very secure. It is probably a remnant of some
old settlement back in the day.
""")

# Returned by the 'tutorial' command.
cliff_well.attributes.add("tutorial_info", """
This is a normal object, locked with the lock get:false() so that
Characters can't pick it up. Since the get_err Attribute is also set,
you get a customized error message when trying to pick it up (that
is checked and echoed by the 'get' command).
""")

# It's important to lock the well object or players will be able to
# pick it up and put it in their pocket...
cliff_well.locks.add("get:false()")

# By setting the lock_msg attribute there will be a nicer error message if 
# people try to pick up the well.
cliff_well.attributes.add("get_err_msg", """
You nudge the heavy stones of the well with a foot. There is no way
you can ever budge this on your own (besides, what would you do with
all those stones? Start your own quarry?).
""")

# -----------------------------------------------------------------------------
#
# The Cliff - Wooden Sign
#
# -----------------------------------------------------------------------------

cliff_sign = create_object(key="Wooden Sign", aliases=["sign"], 
                           typeclass=tutorial_world.objects.Readable,
                           location=cliff)

# Returned by 'look' command.
cliff_sign.db.desc = ("""
The wooden sign sits at the end of a small eastward path. Beyond it
is the shore-side anchor of the hanging bridge that connects the main
land with the castle ruin on its desolate cliff. The sign is not as
old as the rest of the scenery and the text on it is easily readable.
""")

# Returned by the 'tutorial' command.
cliff_sign.attributes.add("tutorial_info", """
This is a readable object, of the Typeclass
evennia.contrib.tutorial_world.objects.Readable. The sign has a cmdset
defined on itself, containing only one command, namely 'read'. This
command is what allows you to 'read sign'. Doing so returns the
contents of the Attribute 'readable_sign', containing the information
on the sign.
""")

# Returned by the 'read' command.
cliff_sign.attributes.add("readable_text", """

|rWARNING - The bridge is not safe!|n

Below this official warning, someone has carved some sprawling
letters into the wood. It reads: "The guardian will not bleed to
mortal blade."
""")

# Prevent from picking up with nice error message.
cliff_sign.locks.add("get:false()")
cliff_sign.attributes.add("get_err_msg", """
The sign is securely anchored to the ground.
""")

# -----------------------------------------------------------------------------
#
# The Cliff - Gnarled Old Tree
# A climbable object for discovering a hidden exit
#
# -----------------------------------------------------------------------------


cliff_tree = create_object(key="gnarled old trees", 
                           aliases=["tree", "trees", "gnarled"], 
                           location=cliff,
                           typeclass=tutorial_world.objects.Climbable)

# Returned by 'look' command.
cliff_tree.db.desc = ("""
Only the sturdiest of trees survive at the edge of the moor. A small group 
of huddling black things has dug in near the cliff edge, eternally pummeled 
by wind and salt to become an integral part of the gloomy scenery.
""")

# Returned by the 'tutorial' command.
cliff_tree.attributes.add("tutorial_info", """
These are climbable objects; they make for a small puzzle for
accessing a hidden exit. Climbing the trees allows the
Climbable typeclass to assign an Attribute on the character
that an exit is then looking for.
""")

# Returned by the 'climb' command.
# Our custom climb command assigns a Tag 'tutorial_climbed_tree' on the 
# climber. The footpath exit will be locked with this tag, meaning that
# it can only be seen/traversed by someone first having climbed.
cliff_tree.attributes.add("climb_text", """
With some effort you climb one of the old trees.


The branches are wet and slippery but can easily carry your
weight. From this high vantage point you can see far and wide.

... In fact, you notice |Ya faint yellowish light|n not far to the north,
beyond the trees. It looks like some sort of building. From this angle
you can make out a |wfaint footpath|n leading in that direction, all
but impossible to make out from ground level. You mentally register
where the footpath starts and will now be able to find it again.


You climb down again.
""")

# Prevent from picking up with nice error message.
cliff_tree.locks.add("get:false()")
cliff_tree.attributes.add("get_err_msg", """
The group of old trees have withstood the eternal wind for hundreds
of years. You will not uproot them any time soon.
""")

# -----------------------------------------------------------------------------
#
# Outside Evennia Inn
# A hidden area which is unlocked by using the 'climb' command on the 
# 'Gnarled old tree' in 'The Cliff' room.
#
# -----------------------------------------------------------------------------

# Returned by the 'look' command.
osinn.db.desc = ("""
You stand outside a one-story sturdy wooden building. Light flickers
behind closed storm shutters. Over the door a sign creaks in the wind
- the writing says |cEvennia Inn|n and the curly letters are
surrounded by a painted image of some sort of snake.  From inside you
hear the sound of laughter, singing and loud conversation.
""")

# Details returned by extended 'look' command.
osinn.db.details = {}

desc = """
The shutters are closed.
"""
osinn.db.details["shutters"] = desc
osinn.db.details["storm"] = desc

desc = """
You think you might have heard of this name before,
but at the moment you can't recall where from.
"""
osinn.db.details["inn"] = desc
osinn.db.details["sign"] = desc

desc = """
The snake is cartoonish with big googly eyes. It looks somewhat
like one of those big snakes from the distant jungles - the kind
squeezes their victims.
"""
osinn.db.details["snake"] = desc
osinn.db.details["letters"] = desc
osinn.db.details["writing"] = desc

# EXITS

osinn_ex1 = create_object(exits.Exit, key="back to cliff", 
                          aliases=["back", "cliff", "south", "s"], 
                          location=osinn, destination=cliff)

osinn_ex2 = create_object(exits.Exit, key="enter", aliases=["in"], 
                          location=osinn, destination=cliff)

# -----------------------------------------------------------------------------
#
# The Evennia Inn
#
# -----------------------------------------------------------------------------

# Returned by the 'look' command.
evinn.db.desc = ("""
The Evennia Inn consists of one large room filled with
tables. The bardisk extends along the east wall, where multiple
barrels and bottles line the shelves. The barkeep seems busy handing
out ale and chatting with the patrons, which are a rowdy and cheerful
lot, keeping the sound level only just below thunderous. This is a
rare spot of warmth and mirth on this dread moor.


Soon you have a beer in hand and are chatting with the locals. Your
eye falls on a |wbarrel|n in a corner with a few old rusty weapons
sticking out. There is a sign next to it: |wFree to take|n. A patron
tells you cheerfully that it's the leftovers from those foolish
adventurers that challenged the old ruin before you ...

(to get a weapon from the barrel, use |wget weapon|n)
""")

# Details returned by extended 'look' command.
evinn.db.details = {}

desc = """
The landlord is a cheerful fellow, always ready to supply you with
more beer. He mentions doing some sort of arcane magic known as
"software development" when not running this place. Whatever that
means.
"""
evinn.db.details["barkeep"] = desc
evinn.db.details["man"] = desc
evinn.db.details["landlord"] = desc

# Returned by the 'tutorial' command.
evinn.attributes.add("tutorial_info", """
Nothing special about this room, only a bonus place to potentially go
for chatting with other online players. Oh, and don't forget to grab
a blade if you don't already have one.
""")

# EXITS
evinn_ex1 = create_object(exits.Exit, key="leave", aliases=["out"], 
                          location=evinn, destination=osinn)


# -----------------------------------------------------------------------------
#
# The Evennia Inn - barrel
# This is the well you will come back up from if you end up in the underground.
#
# -----------------------------------------------------------------------------

evinn_barrel = create_object(tutorial_world.objects.WeaponRack, key="barrel",
                             location=evinn)

# Returned by 'look' command.
evinn_barrel.db.desc = ("""
This barrel has the air of leftovers - it contains an assorted
mess of random weaponry in various states and qualities.
""")

# Prevent from picking up with nice error message.
evinn_barrel.locks.add("get:false()")
evinn_barrel.attributes.add("get_err_msg", """
The barrel is weighed down with random weaponry. This might be the wrong place
to start your weight lifting career.
""")

# Here we set a number of values used by the custom 'get weapon' command.
# This id makes sure that we cannot pick more than one weapon from this rack
evinn_barrel.attributes.add("rack_id", "rack_barrel")
# Set which weapons are available from this rack. These are prototype-keys
# defined in tutorial_world.objects.WEAPON_PROTOTYPES. We also set a
# message to use when trying to grab a second weapon.
evinn_barrel.attributes.add("available_weapons", 
                            ["knife", "dagger", "sword", "club"])
cliff_well.attributes.add("no_more_weapons_msg", """
The barkeep shakes his head. He says: 'Sorry pal. We get a lot of needy
adventurers coming through here. One weapon per person only.'
""")

# -----------------------------------------------------------------------------
#
# The old bridge
# The bridge uses parent tutorial_world.rooms.BridgeRoom, which causes
# the player to take a longer time than expected to cross as they are
# pummeled by wind and a chance to fall off. This room should not have
# regular exits back to the cliff, that is handled by the bridge
# typeclass itself.
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
bridge.db.desc = ("""
The hanging bridge's foundation sits at the edge of the cliff to the
east - two heavy stone pillars anchor the bridge on this side. The
bridge sways precariously in the storm.
""")

# Returned by the 'tutorial' command.
bridge.attributes.add("tutorial_info", """
All of the bridge is actually a single room that uses a custom cmdset
to overrule the movement commands. This makes it take several steps to
cross it despite it being only one room in the database.


The bridge has no normal exits, instead it has a counter that tracks
how far out on the bridge the Character is. For the bridge to work it
needs the names of links to the adjoining rooms, and when the counter
indicates the Character is leaving the bridge, they are teleported
there.


The room also inherits from the weather room to cause the bridge to
sway at regular intervals. It also implements a timer and a random
occurrence at every step across the bridge. It might be worth trying
this passage a few times to see what may happen.  Hint: you can fall
off!
""")

# Set up properties on bridge room (see contrib.tutorial_world.rooms.BridgeRoom)
bridge.attributes.add("west_exit", "tut#02")
# connect other end to gatehouse (Which we will detail later)
bridge.attributes.add("east_exit", "tut#09")
# Fall location is the cliff ledge (detailed next)
bridge.attributes.add("fall_exit", "tut#06")

# -----------------------------------------------------------------------------
#
# Ledge under the bridge
# You only end up at the ledge if you fall off the bridge. It
# has no direct connection to the bridge but we specified
# it as the target of the "fall_exit", which is a special
# feature of the BridgeRoom.
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
ledge.db.desc = ("""
You are on a narrow ledge protruding from the side of the cliff,
about halfway down.  The air is saturated with salty sea water,
sprays hitting your face from the crashing waves |wbelow|n.

The ledge is covered with a few black-grey brushes. Not far from you
the cliff-face is broken down to reveal a narrow natural opening into
the cliff. High above you the |wbridge|n sways and creaks in the wind.
""")

# Details returned by extended 'look' command.
ledge.db.details = {}

desc = """
The brushes covering the ledge are gray and dwarfed from constantly
being pummeled by salt, rain and wind.
"""
ledge.db.details["brush"] = desc
ledge.db.details["brushes"] = desc

desc = """
Below you the gray sea rages, its waves crashing into the cliff so a
thin mist of salt mixes with the rain even this far above it. You can
almost imagine the cliff trembling under its onslaught.
"""
ledge.db.details["below"] = desc
ledge.db.details["sea"] = desc
ledge.db.details["ocean"] = desc
ledge.db.details["waves"] = desc

desc = """
Partly obscured by the rain you can make out the shape of the hanging
bridge high above you. There is no way to get back up there from this
ledge.
"""
ledge.db.details["bridge"] = desc

# Returned by the 'tutorial' command.
intro.attributes.add("tutorial_info", """
This room is stored as an attribute on the 'Bridge' room and used as
a destination should the player fall off the bridge. It is the only
way to get to this room. In our example the bridge is relatively
imple and always drops us to the same ledge; a more advanced
implementation might implement different locations to end up in
depending on what happens on the bridge.
""")

# EXITS
ledge_ex1 = create_object(exits.Exit, key="hole into cliff", 
                          aliases=["hole", "passage", "cliff"], 
                          location=ledge, destination=underground)
ledge_ex1.db.desc = ("""
The hole is natural, the soft rock eroded by ages of sea water. The
opening is small but large enough for you to push through. It looks
like it expands into a cavern further in.
""")

# -----------------------------------------------------------------------------
#
# Underground passages
# The underground passages allow the player to get back up to the
# cliff again. If you look at the map, the 'dark cell' also connects
# to here. We'll get to that later.
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
underground.db.desc = ("""
The underground cavern system you have entered seems to stretch on
forever, with criss-crossing paths and natural caverns probably
carved by water. It is not completely dark, here and there faint
daylight sifts down from above - the cliff is porous leaving channels
of air and light up to the surface.


(some time later)


You eventually come upon a cavern with a black pool of stale
water. In it sits a murky bucket, the first remnant of any sort of
intelligent life down here. The bucket has disconnected from a chain
hanging down from a circular opening high above. Gray daylight
simmers down the hole together with rain that ripples the black
surface of the pool.
""")

# Details returned by extended 'look' command.
underground.db.details = {}

desc = """
The water of the pool is black and opaque. The rain coming down from
above does not seem to ripple the surface quite as much as it should.
"""
underground.db.details["pool"] = desc
underground.db.details["water"] = desc

desc = """
The bucket is nearly coming apart, only rusty iron bands holding
the rotten wood together. It's been down here for a long time.
"""
underground.db.details["bucket"] = desc

desc = """
Whereas the lower edges of the hole seem jagged and natural you can
faintly make out it turning into a man-made circular shaft higher up.
It looks like an old well. There must have been much more water
here once.
"""
underground.db.details["hole"] = desc
underground.db.details["above"] = desc

desc = """
Those dark passages seem to criss-cross the cliff. No need to
head back into the gloom now that there seems to be a way out.
"""
underground.db.details["passages"] = desc
underground.db.details["dark"] = desc

# Returned by the 'tutorial' command.
underground.attributes.add("tutorial_info", """
This room acts as a hub for getting the player back to the
start again, regardless of how you got here.
""")

# EXITS

# From the passages we get back up to the cliff, so we
# open up a new exit back there.
underground_ex1 = create_object(exits.Exit, key="climb the chain", 
                                aliases=["climb", "chain"],
                                location=underground, destination=cliff)
underground_ex1.db.desc = ("""
The chain is made of iron. It is rusty but you think it might still
hold your weight even after all this time. Better hope you don't need
to do this more times ...
""")

# -----------------------------------------------------------------------------
#
# The Dark Cell
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
# The desc is only seen if the player first finds a light source.
cell.db.desc = ("""
|YThe |yflickering light|Y of your makeshift light reveals a small square
cell. It does not seem like you are still in the castle, for the
stone of the walls are chiseled crudely and drip with water and mold.

One wall holds a solid iron-cast door. While rusted and covered with
lichen it seems very sturdy. In a corner lies what might have once
been a bed or a bench but is now nothing more than a pile of splinters,
one of which you are using for light. One of the walls is covered with a
thick cover of black roots having broken through the cracks from the
outside.|n
""")

# Details returned by extended 'look' command.
cell.db.details = {}

desc = """
The door is very solid and clad in iron. No matter how much you push
at it, it won't budge. It actually doesn't show any signs of having
been opened for a very long time.
"""
cell.db.details["iron-cast door"] = desc
cell.db.details["iron"] = desc
cell.db.details["door"] = desc
cell.db.details["iron-cast"] = desc

desc = """
The walls are dripping with moisture and mold. A network of roots
have burst through the cracks on one side, bending the stones
slightly aside. You feel a faint draft from that direction.
"""
cell.db.details["stone walls"] = desc
cell.db.details["walls"] = desc
cell.db.details["stone"] = desc
cell.db.details["stones"] = desc
cell.db.details["wall"] = desc

# Returned by the 'tutorial' command.
cell.attributes.add("tutorial_info", """
Dark room

The dark room implements a custom "dark" state. This is a very
restricted state that completely redefines the look command and only
allows limited interactions.

Looking around repeatedly will eventually produce hints as to how to
get out of the dark room.
""")

# -----------------------------------------------------------------------------
#
# The Dark Cell - Root-Covered Wall
#
# -----------------------------------------------------------------------------

cell_wall = create_object(tutorial_world.objects.CrumblingWall, 
                          key="root-covered wall",
                          aliases=["wall", "roots", "wines", "root"],
                          location=cell)

# (the crumbling wall describes itself, so we don't do it here)

# Returned by the 'tutorial' command.
cell_wall.attributes.add("tutorial_info", """
This room presents a puzzle that has to be solved in order to get out
of the room. The root-covered wall is in fact an advanced Exit-type
object that is locked until the puzzle is solved.
""")

# Prevent from picking up.
cell_wall.locks.add("get:false()")

# The crumbling wall is in fact an advanced type of Exit, all we need to do is
# to supply it with a destination. This destination is auto-assigned to the 
# exit when its puzzle is solved connect to the Underground passages
cell_wall.attributes.add("destination", underground)

# -----------------------------------------------------------------------------
#
# Castle Gate
# We are done with the underground, describe castle.
# The bridge room should not have any normal exits from it, that is
# handled by the bridge itself. So we teleport away from it. The
# ruined gatehouse is also the east_exit target for the bridge as
# we recall.
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
gate.db.desc = ("""
The old gatehouse is near collapse. Part of its northern wall has
already fallen down, together with parts of the fortifications in
that direction.  Heavy stone pillars hold up sections of ceiling, but
elsewhere the flagstones are exposed to open sky. Part of a heavy
portcullis, formerly blocking off the inner castle from attack, is
sprawled over the ground together with most of its frame.

|wEast|n the gatehouse leads out to a small open area surrounded by
the remains of the castle.  There is also a standing archway
offering passage to a path along the old |wsouth|nern inner wall.
""")

# Details returned by extended 'look' command.
gate.db.details = {}

desc = """
This heavy iron grating used to block off the inner part of the gate house, now it has fallen
to the ground together with the stone archway that once help it up.
"""
gate.db.details["portoculis"] = desc
gate.db.details["fall"] = desc
gate.db.details["fallen"] = desc
gate.db.details["grating"] = desc

# Returned by the 'tutorial' command.
gate.attributes.add("tutorial_info", """
This is part of a four-room area patrolled by a mob: the guardian of
the castle. The mob initiates combat if the player stays in the same
room for long enough.

Combat itself is a very simple affair which takes advantage of the
strength of the weapon you use, but dictates a fixed skill for you and
your enemy. The enemy is quite powerful, so don't stick around too
long ...
""")

# We lock the bridge exit for the mob, so it don't wander out on the bridge.
# Only traversing objects controlled by an account (i.e. Characters) may cross
# the bridge.
gate.locks.add("traverse:has_account()")

# EXITS

gate_ex1 = create_object(exits.Exit, key="Bridge over the abyss", 
                         aliases=["bridge", "abyss", "west", "w"],
                         location=gate, destination=bridge)
gate_ex2 = create_object(exits.Exit, key="castle corner", 
                         aliases=["corner", "east", "e"],
                         location=gate, destination=innerwall)
gate_ex3 = create_object(exits.Exit, key="Standing archway", 
                         aliases=["archway", "south", "s"],
                         location=gate, destination=innerwall)
gate_ex3.db.desc = ("""
 It seems the archway leads off into a series of dimly lit rooms.
""")

# -----------------------------------------------------------------------------
#
# Along the southern inner wall (south from gatehouse)
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
innerwall.db.desc = ("""
What appears at first sight to be a series of connected rooms
actually turns out to be collapsed buildings so mashed together by
the ravages of time that they all seem to lean on each other and
against the outer wall. The whole scene is directly open to the sky.

The buildings make a half-circle along the main wall, here and there
broken by falling stone and rubble. At one end (the |wnorth|nern) of
this half-circle is the entrance to the castle, the ruined
gatehoue. |wEast|nwards from here is some sort of open courtyard.
""")

# Returned by the 'tutorial' command.
gate.attributes.add("tutorial_info", """
This is part of a four-room area patrolled by a mob; the guardian of
the castle. The mob initiates combat if the player stays in the same
room for long enough.

Combat itself is a very simple affair which takes advantage of the
strength of the weapon you use, but dictates a fixed skill for you and
your enemy.
""")

# EXITS

innerwall_ex1 = create_object(exits.Exit, key="ruined gatehouse", 
                              aliases=["gatehouse", "north", "n"], 
                              location=innerwall, destination=gate)
innerwall_ex2 = create_object(exits.Exit, key="overgrown courtyard", 
                              aliases=["courtyard", "east", "e"], 
                              location=innerwall, destination=courtyard)

# -----------------------------------------------------------------------------
#
# Corner of castle (east from gatehouse)
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
corner.db.desc = ("""
The ruins opens up to the sky in a small open area, lined by
columns. The open area is dominated by a huge stone |wobelisk|n in its
center, an ancient ornament miraculously still standing.

Previously one could probably continue past the obelisk and eastward
into the castle keep itself, but that way is now completely blocked
by fallen rubble. To the |wwest|n is the gatehouse and entrance to
the castle, whereas |wsouth|nwards the collumns make way for a wide
open courtyard.
""")

# Returned by the 'tutorial' command.
corner.attributes.add("tutorial_info", """
This is part of a four-room area patrolled by a mob; the guardian of
the castle. The mob initiates combat if the player stays in the same
room for long enough.

Combat itself is a very simple affair which takes advantage of the
strength of the weapon you use, but dictates a fixed skill for you and
your enemy.
""")

# EXITS

corner_ex1 = create_object(exits.Exit, key="gatehouse", aliases=["west", "w"], 
                           location=corner, destination=gate)
corner_ex2 = create_object(exits.Exit, key="courtyard", aliases=["south", "s"], 
                           location=corner, destination=courtyard)
# -----------------------------------------------------------------------------
#
# Corner of castle - Obelisk
#
# -----------------------------------------------------------------------------

corner_obelisk = create_object(tutorial_world.objects.Obelisk, 
                               key="obelisk", location=corner)

# Prevent from picking up with nice error message.
corner_obelisk.locks.add("get:false()")
corner_obelisk.attributes.add("get_err_msg", """
It's way too heavy for anyone to move.
""")

# Set the puzzle clues on the obelisk. The order should correspond
# to the ids later checked by the antechamber puzzle.
corner_obelisk.attributes.add("puzzle_descs",
("You can briefly make out the image of |ba woman with a blue bird|n.",
 "You for a moment see the visage of |ba woman on a horse|n.",
 "For the briefest moment you make out an engraving of |ba regal woman wearing a crown|n.",
 "You think you can see the outline of |ba flaming shield|n in the stone.",
 "The surface for a moment seems to portray |ba sharp-faced woman with white hair|n."))

# -----------------------------------------------------------------------------
#
# Corner of castle - Ghostly apparition
#
# -----------------------------------------------------------------------------

corner_mob = create_object(tutorial_world.mob.Mob, 
                           key="Ghostly apparition", 
                           aliases=["ghost", "apparition", "fog"], 
                           location=corner)

# Set its home to this location
corner_mob.attributes.add("home", corner)

# Prevent from picking up with nice error message.
corner_mob.locks.add("get:false()")
corner_mob.attributes.add("get_err_msg", """
Your fingers just pass straight through it!
""")

corner_mob.attributes.add("desc_alive", """
This ghostly shape could momentarily be mistaken for a thick fog had
it not moved with such determination and giving echoing hollow
screams as it did. The shape is hard to determine, now and then it
seems to form limbs and even faces that fade away only moments
later. The thing reeks of almost tangible spite at your
presence. This must be the ruin's eternal guardian.
""")

corner_mob.attributes.add("desc_dead", """
The ghostly apparition is nothing but a howling on the wind, an eternal
cold spot that can never be fully eradicated from these walls. While harmless
in this state, there is no doubt that it shall eventually return to this plane
to continue its endless haunting.
""")

# We set the ghost to send defeated enemies to the Dark Cell
corner_mob.attributes.add("send_defeated_to", cell)

corner_mob.attributes.add("defeat_msg", """
You fall to the ground, defeated. As you do, the ghostly apparition dives
forward and engulf you.


The world turns black.
""")

corner_mob.attributes.add("defeat_msg_room", """
%s falls to the ground, defeated. For a moment their fallen form is
engulfed by the swirling mists of the ghostly apparition. When they
raise lift, the ground is empty!
""")

corner_mob.attributes.add("weapon_ineffective_msg", """
Your weapon just passes through the swirling mist of the ghostly apparition, causing no effect!
""")

corner_mob.attributes.add("hit_msg", """
The ghostly apparition howls and writhes, shifts and shivers.
""")

corner_mob.attributes.add("death_msg", """
After the last strike, the ghostly apparition seems to collapse
inwards. It fades and becomes one with the mist. Its howls rise to a
ear-shattering crescendo before quickly fading away to be nothing more
than the lonely cries of the cold, salty wind.
""")

# Give the enemy some random echoes (echoed at irregular intervals)
corner_mob.attributes.add("irregular_msgs",
["The foggy thing gives off a high-pitched shriek.",
 "For a moment the fog wraps around a nearby pillar.",
 "The fog drifts lower to the ground as if looking for something.",
 "The fog momentarily takes on a reddish hue.",
 "The fog temporarily fills most of the area as it changes shape.",
 "You accidentally breathes in some of the fog - you start coughing from the cold moisture."])

# Give the enemy a tentacle weapon
mob_weapon = create_object(tutorial_world.objects.Weapon, 
                           key="foggy tentacles", aliases=["tentacles"], 
                           location=corner_mob)

# Make the enemy's weapon good - hits at 70% of attacks, but not good at parrying.
mob_weapon.attributes.add("hit", "0.7")
mob_weapon.attributes.add("parry", "0.1")
mob_weapon.attributes.add("damage", "5")

# Start the mob
corner_mob.set_alive()

# -----------------------------------------------------------------------------
#
# The courtyard
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
courtyard.db.desc = ("""
The inner courtyard of the old castle is littered with debris and
overgrown with low grass and patches of thorny vines. There is a
collapsed structure close to the gatehouse that looks like a stable.

|wNorth|nwards is a smaller area cornered in the debris, adorned with
a large obelisk-like thing. To the |wwest|n the castle walls loom
over a mess of collapsed buildings. On the opposite, |weast|nern side
of the yard is a large building with a curved roof that seem to have
withstood the test of time better than many of those around it, it
looks like some sort of temple.
""")

# Details returned by extended 'look' command.
courtyard.db.details = {}

desc = """
The building is empty, if it was indeed once a stable it was abandoned long ago.
"""
courtyard.db.details["stables"] = desc
courtyard.db.details["stable"] = desc
courtyard.db.details["building"] = desc

# Returned by the 'tutorial' command.
courtyard.attributes.add("tutorial_info", """
This is part of a four-room area patrolled by a mob; the guardian of
the castle. The mob initiates combat if the player stays in the same
room for long enough.

Combat itself is a very simple affair which takes advantage of the
strength of the weapon you use, but dictates a fixed skill for you and
your enemy.
""")

# EXITS

courtyard_ex1 = create_object(exits.Exit, key="castle corner", 
                              aliases=["north", "n"], 
                              location=courtyard, destination=corner)
courtyard_ex2 = create_object(exits.Exit, key="along inner wall", 
                              aliases=["wall", "along", "west", "w"],
                              location=courtyard, destination=innerwall)
courtyard_ex3 = create_object(exits.Exit, key="ruined temple", 
                              aliases=["temple", "east", "e"],
                              location=courtyard, destination=temple)

# -----------------------------------------------------------------------------
#
# The temple
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
temple.db.desc = ("""
This building seems to have survived the ravages of time better than
most of the others. Its arched roof and wide spaces suggests that
this is a temple or church of some kind.


The wide hall of the temple stretches before you. At the far edge is
a stone altar with no clear markings. Despite its relatively good
condition, the temple is empty of all furniture or valuables, like it
was looted or its treasures moved ages ago.

Stairs lead down to the temple's dungeon on either side of the
altar. A gaping door opening shows the a wide courtyard to the west.
""")

# Details returned by extended 'look' command.
temple.db.details = {}

desc = """
The altar is a massive stone slab. It might once have had ornate decorations
but time and the salty air has broken everything down into dust.
"""
temple.db.details["altar"] = desc

desc = """
The dome still looming intact above you is a marvel of engineering.
"""
temple.db.details["ceiling"] = desc


# EXITS

temple_ex1 = create_object(exits.Exit, key="overgrown courtyard", 
                           aliases=["courtyard", "outside", "out", "west", "w"], 
                           location=temple, destination=courtyard)
temple_ex2 = create_object(exits.Exit, key="stairs down", 
                           aliases=["stairs", "down", "d"], 
                           location=temple, destination=antechamber)                           
temple_ex2.db.desc = ("""
The stairs are worn by the age-old passage of feet.
""")

# Lock the antechamber so the ghost cannot get in there.
temple_ex2.locks.add("traverse:has_account()")

# -----------------------------------------------------------------------------
#
# Antechamber - below the temple
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
antechamber.db.desc = ("""
This chamber lies almost directly under the main altar of the
temple. The passage of aeons is felt here and you also sense you are
close to great power.

The sides of the chamber are lined with stone archways, these are
entrances to the |wtombs|n of what must have been influential
families or individual heroes of the realm. Each is adorned by a
stone statue or symbol of fine make. They do not seem to be ordered
in any particular order or rank.
""")

# Returned by the 'tutorial' command.
antechamber.attributes.add("tutorial_info", """
This is the second part of a puzzle involving the Obelisk in the
castle's north-east corner. The correct exit to use will vary
depending on which scene was shown on the Obelisk surface.

Each tomb is a teleporter room and is keyed to a number corresponding
to the scene last shown on the obelisk (now stored on player). If the
number doesn't match, the tomb is a trap that teleports to a second
Teleporter room describing how you fall in a trap - that room then
directly relay you on to the Dark Cell. If correct, the tomb
teleports to the Ancient Tomb treasure chamber.
""")

# EXITS

antechamber_ex1 = create_object(exits.Exit, key="up the stairs to ruined temple", 
                                aliases=["stairs", "temple", "up", "u"],
                                location=antechamber, destination=temple)
antechamber_ex2 = create_object(exits.Exit, key="Blue bird tomb", 
                                aliases=["bird", "blue", "stone"],
                                location=antechamber, destination=bird)
antechamber_ex2.db.desc = ("""
The entrance to this tomb is decorated with a very lifelike blue bird.
""")

antechamber_ex3 = create_object(exits.Exit, key="Tomb of woman on horse", 
                                aliases=["horse", "riding"],
                                location=antechamber, destination=horse)
antechamber_ex3.db.desc = ("""
The entrance to this tomb depicts a scene of a strong warrior woman on a black
horse. She shouts and brandishes a glowing weapon as she charges down a hill 
towards some enemy not depicted.
""")

antechamber_ex4 = create_object(exits.Exit, key="Tomb of the crowned queen", 
                                aliases=["crown", "queen"],
                                location=antechamber, destination=crown)
antechamber_ex4.db.desc = ("""
The entrance to this tomb shows a beautiful mural of a queen ruling
from her throne, respectful subjects kneeling before her. On her head
is a crown that seems to shine with magical power.
""")

antechamber_ex5 = create_object(exits.Exit, key="Tomb of the shield", 
                                aliases=["shield"],
                                location=antechamber, destination=shield)
antechamber_ex5.db.desc = ("""
This tomb shows a warrior woman fighting shadowy creatures from the
top of a hill. Her sword lies broken on the ground before her but she
fights on with her battered shield - the scene depicts her just as she
rams the shield into an enemy in wild desperation.
""")

antechamber_ex6 = create_object(exits.Exit, key="Tomb of the hero", 
                                aliases=["knight", "hero", "monster", "beast"],
                                location=antechamber, destination=hero)
antechamber_ex6.db.desc = ("""
The entrance to this tomb shows a mural of an aging woman in a
warrior's outfit. She has white hair yet her sword-arm shows no sign
of weakness and her pose is straight. Children are gathered around her
feet and men and women from all the land come to seek the wisdom and
strength of the legendary hero.
""")


# -----------------------------------------------------------------------------
#
# Blue Bird Tomb
# We create all the tombs. These all teleport to the dark cell
# except one which is the one decided by the scene shown by the
# Obelisk last we looked.
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

bird.attributes.add("puzzle_value", "0")
bird.attributes.add("failure_teleport_to", cell)
bird.attributes.add("success_teleport_to", tomb)

bird.attributes.add("failure_teleport_msg", """
The tomb is dark. You fumble your way through it. You think you can
make out a coffin in front of you in the gloom.


|rSuddenly you hear a distinct 'click' and the ground abruptly
disappears under your feet! You fall ... things go dark. |n


...


... You come to your senses. You lie down. On stone floor. You
shakily come to your feet. Somehow you suspect that you are not under
the tomb anymore, like you were magically snatched away.

The air is damp. Where are you?
""")

bird.attributes.add("success_teleport_msg", """
The tomb is dark. You fumble your way through it. You think you can
make out a coffin in front of you in the gloom.

The coffin comes into view. On and around it are chiseled scenes of a
stern woman in armor. They depict great heroic deeds. This is clearly
the tomb of some sort of ancient heroine - it must be the goal you
have been looking for!
""")

# -----------------------------------------------------------------------------
#
# Tomb of woman on horse
# We create all the tombs. These all teleport to the dark cell
# except one which is the one decided by the scene shown by the
# Obelisk last we looked.
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

horse.attributes.add("puzzle_value", "1")
horse.attributes.add("failure_teleport_to", cell)
horse.attributes.add("success_teleport_to", tomb)

horse.attributes.add("failure_teleport_msg", """
The tomb is dark. You fumble your way through it. You think you can
make out a coffin in front of you in the gloom.


|rSuddenly you hear a distinct 'click' and the ground abruptly
disappears under your feet! You fall ... things go dark. |n


...


... You come to your senses. You lie down. On stone floor. You
shakily come to your feet. Somehow you suspect that you are not under
the tomb anymore, like you were magically snatched away.

The air is damp. Where are you?
""")

horse.attributes.add("success_teleport_msg", """
The tomb is dark. You fumble your way through it. You think you can
make out a coffin in front of you in the gloom.

The coffin comes into view. On and around it are chiseled scenes of a
stern woman in armor. They depict great heroic deeds. This is clearly
the tomb of some sort of ancient heroine - it must be the goal you
have been looking for!
""")

# -----------------------------------------------------------------------------
#
# Tomb of the crowned queen
# We create all the tombs. These all teleport to the dark cell
# except one which is the one decided by the scene shown by the
# Obelisk last we looked.
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

crown.attributes.add("puzzle_value", "2")
crown.attributes.add("failure_teleport_to", cell)
crown.attributes.add("success_teleport_to", tomb)

crown.attributes.add("failure_teleport_msg", """
The tomb is dark. You fumble your way through it. You think you can
make out a coffin in front of you in the gloom.


|rSuddenly you hear a distinct 'click' and the ground abruptly
disappears under your feet! You fall ... things go dark. |n


...


... You come to your senses. You lie down. On stone floor. You
shakily come to your feet. Somehow you suspect that you are not under
the tomb anymore, like you were magically snatched away.

The air is damp. Where are you?
""")

crown.attributes.add("success_teleport_msg", """
The tomb is dark. You fumble your way through it. You think you can
make out a coffin in front of you in the gloom.

The coffin comes into view. On and around it are chiseled scenes of a
stern woman in armor. They depict great heroic deeds. This is clearly
the tomb of some sort of ancient heroine - it must be the goal you
have been looking for!
""")

# -----------------------------------------------------------------------------
#
# Tomb of the shield
# We create all the tombs. These all teleport to the dark cell
# except one which is the one decided by the scene shown by the
# Obelisk last we looked.
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

shield.attributes.add("puzzle_value", "3")
shield.attributes.add("failure_teleport_to", cell)
shield.attributes.add("success_teleport_to", tomb)

shield.attributes.add("failure_teleport_msg", """
The tomb is dark. You fumble your way through it. You think you can
make out a coffin in front of you in the gloom.


|rSuddenly you hear a distinct 'click' and the ground abruptly
disappears under your feet! You fall ... things go dark. |n


...


... You come to your senses. You lie down. On stone floor. You
shakily come to your feet. Somehow you suspect that you are not under
the tomb anymore, like you were magically snatched away.

The air is damp. Where are you?
""")

shield.attributes.add("success_teleport_msg", """
The tomb is dark. You fumble your way through it. You think you can
make out a coffin in front of you in the gloom.

The coffin comes into view. On and around it are chiseled scenes of a
stern woman in armor. They depict great heroic deeds. This is clearly
the tomb of some sort of ancient heroine - it must be the goal you
have been looking for!
""")

# -----------------------------------------------------------------------------
#
# Tomb of the hero
# We create all the tombs. These all teleport to the dark cell
# except one which is the one decided by the scene shown by the
# Obelisk last we looked.
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

shield.attributes.add("puzzle_value", "4")
shield.attributes.add("failure_teleport_to", cell)
shield.attributes.add("success_teleport_to", tomb)

shield.attributes.add("failure_teleport_msg", """
The tomb is dark. You fumble your way through it. You think you can
make out a coffin in front of you in the gloom.


|rSuddenly you hear a distinct 'click' and the ground abruptly
disappears under your feet! You fall ... things go dark. |n


...


... You come to your senses. You lie down. On stone floor. You
shakily come to your feet. Somehow you suspect that you are not under
the tomb anymore, like you were magically snatched away.

The air is damp. Where are you?
""")

shield.attributes.add("success_teleport_msg", """
The tomb is dark. You fumble your way through it. You think you can
make out a coffin in front of you in the gloom.

The coffin comes into view. On and around it are chiseled scenes of a
stern woman in armor. They depict great heroic deeds. This is clearly
the tomb of some sort of ancient heroine - it must be the goal you
have been looking for!
""")

# -----------------------------------------------------------------------------
#
# The ancient tomb
#
# This is the real tomb, the goal of the adventure. It is not
# directly accessible from the Antechamber but you are
# teleported here only if you solve the puzzle of the Obelisk.
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
tomb.db.desc = ("""
Apart from the ornate sarcophagus, the tomb is bare from extra decorations.
This is the resting place of a warrior with little patience for
glamour and trinkets. You have reached the end of your quest.
""")

# Returned by the 'tutorial' command.
tomb.attributes.add("tutorial_info", """
Congratulations, you have reached the end of this little tutorial
scenario. Just grab the mythical weapon (get weapon) and the exit
will open.

You can end the quest here or go back through the tutorial rooms to
explore further. You will find this weapon works better against the
castle's guardian than any of the others you have found ...
""")

# EXITS

tomb_ex1 = create_object(exits.Exit, key="back to antechamber", 
                         aliases=["antechamber", "back"], 
                         location=tomb, destination=antechamber)
tomb_ex2 = create_object(exits.Exit, key="Exit tutorial", 
                         aliases=["exit", "end"], 
                         location=tomb, destination=exit)
                         
# All weapons from the rack gets an automatic alias the same as the
# rack_id. This we can use to check if any such weapon is in inventory
# before unlocking the exit.
tomb_ex2.locks.add("view:tag(rack_sarcophagus, tutorial_world) ; traverse:tag(rack_sarcophagus, tutorial_world)")

# -----------------------------------------------------------------------------
#
# The ancient tomb - Sarcophagus
#
# The sarcophagus is a "weapon rack" from which you can extract one
# single weapon.
#
# -----------------------------------------------------------------------------

tomb_sarcophagus = create_object(tutorial_world.objects.WeaponRack, 
                                 key="Stone sarcophagus", location=tomb,
                                 aliases=["sarcophagus", "stone"])

# Returned by the 'look' command.
tomb_sarcophagus.db.desc = ("""
The lid of the coffin is adorned with a stone statue in full size.
The weapon held by the stone hands looks very realistic ...

The hands of the statue close on what seems to be a real weapon
rather than one in stone.  This must be the hero's legendary weapon!
The prize you have been looking for!

(try |wget weapon|n)
""")

corner_obelisk.attributes.add("rack_id", "rack_sarcophagus")
corner_obelisk.attributes.add("available_weapons", ["ornate longsword",
                                                    "warhammer", "rune axe",
                                                    "thruning", "slayer waraxe",
                                                    "ghostblade", "hawkblade"])
corner_obelisk.attributes.add("no_more_weapons_msg", """
The tomb has already granted you all the might it will ever do.
""")
corner_obelisk.attributes.add("get_weapon_msg", """
Trembling you carefully release the weapon from the stone to test
its weight. You are finally holding your prize,

The |c%s|n

in your hands!

|gThis concludes the Evennia tutorial. From here you can either
continue to explore the castle (hint: this weapon works better
against the castle guardian than any you might have found earlier) or
you can choose to exit.|n
""")

# -----------------------------------------------------------------------------
#
# Outro - end of the tutorial
#
# This cleans all temporary attributes set on the Character
# by the tutorial, removes weapons and items etc.
#
# -----------------------------------------------------------------------------

# ROOM DETAILS

# Returned by the 'look' command.
exitroom.db.desc = ("""
|gThanks for trying out this little Evennia tutorial!


The game play given here is of course just scraping the surface of
what can be done with Evennia. The tutorial focuses more on showing
various techniques than to supply any sort of novel storytelling or
gaming challenge.  The full README and source code for the tutorial
world can be found under |wcontrib/tutorial_world|g.


If you went through the tutorial quest once, it can be interesting to
do it again to explore the various possibilities and rooms you might
not have come across yet, maybe with the source/build code next to
you.  If you play as superuser (user #1) the mobile will ignore you
and teleport rooms etc will not affect you (this will also disable all
locks, so keep that in mind when checking functionality).|n
""")

# Returned by the 'tutorial' command.
exitroom.attributes.add("tutorial_info", """
This room cleans up all temporary attributes and tags that were put
on the character during the tutorial. Hope you enjoyed the play
through!
""")

# we want to clear the weapon-rack ids on the character when exiting.
exitroom.attributes.add("wracklist", ["rack_barrel", "rack_sarcophagus"])

# EXITS

exitroom_ex1 = create_object(exits.Exit, key="Exit Tutorial", aliases=["exit"],
                             location=exit, destination=caller.location)
