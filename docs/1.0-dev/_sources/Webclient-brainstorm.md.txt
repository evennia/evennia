# Webclient brainstorm

# Ideas for a future webclient gui

*This is a brainstorming whitepage. Add your own comments in a named section below.*

## From Chat on 2019/09/02
```
  Griatch (IRC)APP  @friarzen: Could one (with goldenlayout) programmatically provide pane positions
and sizes?
I recall it was not trivial for the old split.js solution.
  friarzen  take a look at the goldenlayout_default_config.js
It is kinda cryptic but that is the layout json.
  Griatch (IRC)APP  @friarzen: Hm, so dynamically replacing the goldenlayout_config in the global
scope at the right
 thing would do it?
  friarzen  yep
  friarzen  the biggest pain in the butt is that goldenlayout_config needs to be set before the
goldenlayout init()
is called, which isn't trivial with the current structure, but it isn't impossible.
  Griatch (IRC)APP  One could in principle re-run init() at a later date though, right?
  friarzen  Hmm...not sure I've ever tried it... seems doable off the top of my head...
right now, that whole file exists to be overridden on page load as a separate <script> HTML tag, so
it can get
force-loaded early.
you could just as easily call the server at that time for the proper config info and store it into
the variable.
  Griatch (IRC)APP  @friarzen: Right. I picture the default would either be modified directly in
that file or even be
in settings.
  friarzen  And if you have it call with an authenticated session at that early point, you could
even have the layout
be defined as a per-user setting.
  Griatch (IRC)APP  Yeah, I think that'd be a very important feature.
So one part of the config would be the golden-layout config blob; then another section with custom
per-pane
settings. Things like which tag a pane filters on, its type, and options for that type (like
replace/scroll for a
text pane etc).
And probably one general config section; things like notifications, sounds, popup settings and the
like
  friarzen  Actually, that information is already somewhat stored into the data as componentState {}
  Griatch (IRC)APP  I imagine a pane would need to be identified uniquely for golden-layout to know
which is which,
so that'd need to be associated.
  friarzen  see line 55.
that's....where it gets tricky...
goldenlayout is kinda dumb in that it treats the whole json blob as a state object.
  Griatch (IRC)APP  componentState, is the idea that it takes arbitrary settings then?
  friarzen  so each sub-dictionary with a type of "component" in it is a window and as you move
stuff around it
dynamically creates new dictionaries as needed to keep it all together.
yep
right now I'm storing the list of types as a string and the updateMethod type as a string, just to
be as obvious as
possible.
  Griatch (IRC)APP  I wonder if one could populate componentState(s) just before initializing the
system, and then
extract them into a more Evennia-friendly storage when saving. Or maybe it's no big deal to just
store that whole
blob as-is, with some extra things added?
  friarzen  if you want to see it in action, take a look at the values in your localstorage after
you've moved stuff
around, created new windows, etc.
I think their preference is to just store the whole blob.
which is what the localstorage save does, in fact.
  Griatch (IRC)APP  Yes, I see.
It allows you to retain the session within your browser as well
  friarzen  One trick I've been thinking about for the whole interface is to have another pair of
components, one
being a "dynamic" config window that displays a series of dropdowns, one for each plugin that
defines it's own
settings.
And another that has an embedded i-frame to allow a split-screen where half of the display is the
text interface
and the other loads the local main website page and allows further browsing.
  Griatch (IRC)APP  I think ideally, each pane should handle its per-pane settings as a dropdown or
popup triggered
from its header.
  friarzen  well, pane != plugin...
  Griatch (IRC)APP  True, one tends to sometimes make the other available but they are not the same
  friarzen  think of the history plugin for example...if you want to make keyboard keys dynamically
configurable, you
need some place to enter that information.
yeah.
  Griatch (IRC)APP  Yes, I buy that - a dynamical option window would be needed. I'd say the
'global' settings should
be treated as just another module in this regard though
So that if you have no modules installed, there is one entry in that option pane, the one that opens
the global
options
  friarzen  Yeah, so that is that component...one pane.
  Griatch (IRC)APP  Another thing that the config should contain would be the available message
tags. Waiting for
them to actually show up before being able to use them is not that useful. This would likely have to
be a setting
though I imagine.
  friarzen  we could remove the current pop-up and just open the new component pane instead, and
then that pane would
display the list of plugins that registered a config() callback.
  Griatch (IRC)APP  Yes
  friarzen  yeah, the server has to pre-define what tags it is going to send.
  Griatch (IRC)APP  The process for adding a tag would be to adding to, say, a list in settings,
restart and then .. profit
  friarzen  yep, which is kind of how I see spawns working.
  Griatch (IRC)APP  spawns, meaning stand-alone windows?
  friarzen  we just have a plugin that defines it's config pane with a "match this text" box and a
tag type to send
the data to, or spawn a new pane with that tag type preselected to capture that text.
wouldn't be stand alone windows.  just new tabs, for now.
  Griatch (IRC)APP  Ok, so a filter target that filters on text content and directs to tag
  friarzen  yep.
  Griatch (IRC)APP  (or re-tags it, I suppose)
  friarzen  yeah, exactly.
and opens a new window for that tag if one doesn't already exist.
  Griatch (IRC)APP  A lot of complex effects could be achieved there. Should the filter extract the
text and re-tag,
or should it keep the text with its original tag and make a copy of it with the new tag? O_o;
  friarzen  yet more options for the user. :slightly_smiling_face:
baby steps first I think.
"pages from bob should go to bob's window, not the general chat window"
  Griatch (IRC)APP  It doesn't sound too hard to do - using tagging like that is really neat since
then the rerouting
can just work normally without knowing which pane you are actually rerouting too (and you could have
multiple panes
getting the same content too)
  friarzen  yep.
and the i-frame component, I think, provides just as much wow facter.
  Griatch (IRC)APP  Yes, the setting would be something like: If text contains "bob" -> set tag
"bob" (auto-create
pane if not exist []?)
  friarzen  just being able to load a character page from the wiki side in half the screen
(including the pictures
and whatnot) while playing/reading the text from the other half is really nice.
  Griatch (IRC)APP  Could there not be some cross-scripting warnings in modern browsers if trying to
load another
website in an iframe?
I doubt you could open Github like that, for example.
friarzen  well, assuming it is all from the same origin game server, it will all be from the same
domain, so should
avoid that, but it will take some testing to make sure.  I want to get it to the point where you can
click on
somebody's name in the general terminal-style window and have it pop up that characters' wiki page.
  Griatch (IRC)APP  That does sound nice :)
  friarzen  i-frames are pretty much the only way to handle cross-domain content, but they are a
pain in the butt to
get that to work.
  Griatch (IRC)APP  If it's on the same domain it would be fine, but it should probably give a "you
are now leaving
..." message and switch to a new window if going elsewhere.
  friarzen  (without getting into modern CORS url blessings)
yeah
  Griatch (IRC)APP  Just to avoid headaches :)
  friarzen  So, yeah, two new goldenlayout components that I am working on but they aren't ready
yet. heh.
  Griatch (IRC)APP  Oh, you are working on them already?
  friarzen  yeah, some initial "will this work" structure.
I haven't found anything yet that will not make it work.
it's mostly just not going to look very pretty to start with. It'll take a few iterations I bet.
  Griatch (IRC)APP  Sounds good! We should probably try to formalize our thoughts around a future
config format as
well. Depending just how and when the golden-layout blob needs to be in place and if we can
construct it on-the-
fly, it affects the format style chosen.
  friarzen  Yeah, that's new from today's conversation, so I don't really have anything built for
that.
  Griatch (IRC)APP  I'm still unsure about how the Evennia/pane specific things (that'd need to be
serialized to the
database on a per-account basis) would interact with the golden-layout structure.
  friarzen  maybe the place to start is to wipe-out/update the old
https://github.com/evennia/evennia/wiki/Webclient-
brainstorm entry?
  Griatch (IRC)APP  I don't think we need to wipe the old, but we could certainly add a new section
above the old and
start some new discussions.
  friarzen  It is really just that per componentState bit.
anything in that json is treated as a blackbox that goldenlayout just passes around.
  Griatch (IRC)APP  So would we save the whole blob then, componentState and all, and simply not
worry about
ourselves storing per-pane options?
The drawback with that would be that a dev could not offer an exact default layout/setup for the
user.
... unless they set it up and saved the blob I guess
  friarzen  Yeah, that's exactly how I built mine. :slightly_smiling_face:
not the most dev-friendly way to do it, but it works.
  Griatch (IRC)APP  Heh. Ok, so the config would be one section for the golden-layout-blob, one for
module settings,
one of which is the global settings.
and a list of the available tags
  friarzen  yep
  Griatch (IRC)APP  And probably an empty misc section for future use ...
  friarzen  seems reasonable.
  Griatch (IRC)APP  So, that means that in the future one would need a procedure for the dev to
easily create and
save the player-wide default to central storage. Well, one step at a time.
For now, good night!
  friarzen  Yep, I expect that would be some kind of admin-approved api/command
  Griatch (IRC)APP  And thanks for the discussion!
```


---

Relates to the activity happening relating to the [Webclient extensions task
#614](https://github.com/evennia/evennia/issues/614).

## Griatch Jan 23, 2017 post 2

These are my ideas for the functionality of Evennia's webclient in the (possibly distant) future. It
assumes the webclient options have been implemented as per
[#1172](https://github.com/evennia/evennia/pull/1172).

![Mockup 1][webclient_mockup_1]

The idea of the GUI is based around *panes* (a "window" feels like something that pops open). These
are areas of the window of the type you would see from a javascript library like
[Split.js](https://nathancahill.github.io/Split.js/). Each pane has a separator with a handle for
resizing it.

Each pane has an icon for opening a dropdown menu (see next mockup image). 

Above image could show the default setup; mimicking the traditional telnet mud client setup. There
should be at least one input pane (but you could add multiple). The Input pane has the icon for
launching the main webclient options window. *Alternatively the options icon could hover
transparently in the upper left, "above" all panes*.

The main webclient options window should have an option for hiding all GUI customization icons (the
draggable handles of panes and the dropdown menu) for users who does not want to have to worry about
changing things accidentally. Devs not wanting to offer players the ability to customize their
client GUIs could maybe just set it up the way they want and then turn the gui controls off on the
javascript level.

![Mockup 2][webclient_mockup_2]

The dropdown menu allows for splitting each pane horizontally and vertically.

![Mockup 3][webclient_mockup_3]

Each pane is "tagged" with what data will be sent to it. It could accept more than one type of
tagged data. Just which tags are available is different for each game (and should be reported by the
server).

For example, the server could send the return of the "look" command as 

```python
    msg("you see ...", {"pane": "look"})
```

If one (or more) of the panes is set to receive "look" data, all such will go there. If *no* pane is
assigned to "look", this text will end up in the pane(s) with the "Unassigned" designation. It might
be necessary to enforce that at least one window has the "unassigned" designation in order to not
lose output without a clear pane target. By contrast the pane tagged with "All" receives all output
regardless of if it is also being sent to other panes.

Another thing that came to mind is logging. It might be an idea to tie a given log file to a
specific pane (panes?) to limit spam in the log (it might be one reason for having a pane with the
"All" tag, for those wanting to log *everything*). This could also be set in the dropdown menu or in
the webclient options window, maybe.

Comments?

## titeuf87 Jan 23, 2017
That way of splitting panes seems easy to manage while still being powerful at the same time.
It's certainly a lot more flexible than what I had in mind.

This is a quick sketch of what I was thinking about:

```
=====================
Options           [x]
=====================
help:         [popup]
map:       [top left]
channels: [top right]
look:   [main output]
```
But that's not as good as Griatch's proposal.


The panes themselves can work differently depending on the content though:

* channel messages: when someone talks on a channel, the output text needs to be appended to the
text already shown.
* inventory: this pane should clear its output every time the inventory is displayed, so old
inventory is not displayed. Also what about dropping items? As long as the player doesn't check its
inventory then that pane won't be updated, unless more OOB data is added to track the inventory.
* help/look: those pane should probably also clear their content before displaying new content.

logging: do you mean have a "save to log" item in the pane menu?

## Griatch Jan 23, 2017, post 1

It makes sense that different types of panes would have different functionality. I was thinking that
something like `inventory` would be very specific to a given game. But titeuf87 has a point - maybe
you can get a rather generalized behavior just by defining if a pane should replace or append to the
existing data.

As for the updating of inventory when dropping items, not sure if that can be generalized, but I
guess drop/get commands could be wired to do that.

As for logging - yes I picture a "save to log" thing in the menu. The problem is just where to save
the log. I think at least for an initial setup, one could maybe set the logging file path in the
webclient options and just append logs from all the panes marked for logging to that same file.

[webclient_mockup_1]:
https://cloud.githubusercontent.com/assets/294267/22219738/448795f0-e1ac-11e6-9a31-222d8ac7f297.png
[webclient_mockup_2]:
https://cloud.githubusercontent.com/assets/294267/22219743/4cf18a84-e1ac-11e6-9d1a-307c0db94419.png
[webclient_mockup_3]:
https://cloud.githubusercontent.com/assets/294267/22219746/511151f8-e1ac-11e6-8445-9cdfd4b9ab5d.png

## chainsol 3rd of October, 2017
I've been messing a little bit with split.js - I've managed to split a split dynamically with a data
attribute on a button and jQuery. My current thinking on this issue is to use [jQuery
Templates](http://codepb.github.io/jquery-template/) to write the template for horizontal and
vertical splits, then using jQuery to set up the initial split layout by inserting those templates
as appropriate for user settings.

We would have a dropdown per split that decides what tag it's meant to handle - perhaps a data
attribute that we change in the template for easy selection through jQuery - and then send tags for
messages to the webclient. This dropdown would also have a setting per split to either append new
content or replace content - again, perhaps a data attribute.

We might also want to store "mobile" and "desktop" layouts separately - or just default to a mobile-
friendly layout at a certain screen size, and turn off the splits.

Oh, and embedding Bootstrap containers in splits works perfectly - that could help us too.

## chainsol 9th of October, 2017
I've got a demo of this working at [my development box](https://dev.perfectdisorder.net/webclient),
if anyone wants to take a look. So far, I've got tag handling, dynamic splits, and the ability to
swap splits' contents. Since this doesn't have a fancy interface yet, if you want to see a dynamic
split, open your browser's console and try these commands:

`SplitHandler.split("#main", "horizontal")` will split the top-half into two 50-50 splits, both
receiving content that's not tagged or is tagged "all" from the server.

`SplitHandler.swapContent("#input", "#split_2")` after doing so will swap the input into the top-
left split.

I'm trying to figure out where to put each split's configuration - maybe a dropdown button that's
semi-transparent until you hover over it? So far, if you edited the data attributes, you could
change each split to receive only tagged messages ( data-tag="all" ), and you could change them to
overwrite instead of append data ( data-update-append or data-update-overwrite )

## Griatch Oct 13, 2017

I would suggest that, assuming the game dev allows the user to modify their GUI in the first place,
that modification is a "mode". I picture that 99% of the time a user doesn't need to modify their
interface. They only want to click whatever game-related buttons etc are present in the pane without
risk of resizing things accidentally.

So I'd say that normally the panes are all fixed, with minimal spacing between them, no handles etc.
But you can enter the client settings window and choose *Customize GUI mode* (or something like
that). When you do, then separators get handles and the dropdown menu markers appear (permanently)
in the corner of each pane. This means that if a user *wants* to easily tweak their window they
could stay in this mode, but they could also "lock" the gui layout at any time.