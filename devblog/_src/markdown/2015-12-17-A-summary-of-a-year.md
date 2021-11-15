### [A summary of a year](https://evennia.blogspot.com/2015/12/a-summary-of-year.html)

[![](https://4.bp.blogspot.com/-_8Yxtk6y1KQ/VnLiQf1U18I/AAAAAAAAEew/7zabQTvUEdY/s200/33-1196545384.jpg)](https://4.bp.blogspot.com/-_8Yxtk6y1KQ/VnLiQf1U18I/AAAAAAAAEew/7zabQTvUEdY/s1600/33-1196545384.jpg)

As 2015 is slowly drawing to an end, I looked back through Evennia's repository to see just what was going on this year. And it turns out it was a lot! I honestly didn't remember some things happened as recently as they did.  
  
_Note: For those reading this not familiar with Evennia, it's a Python library for creating MUDs (text-based multiplayer games)._  
   
  

## Making Evennia into a library

In February of 2015 we merged what was likely the biggest change happening for a good while in Evennia - the complete refactoring of the Evennia repository into a library. It used to be that when you cloned the Evennia repo, it would come with a pre-made game/ folder where you were supposed to put your custom files. Mixing the stuff you downloaded from us with your own files (which you might want to keep under version control of your own) was not a very clean solution.  
  
In the big "library update", we instead created a stand-alone evennia program which you use to create your own "game dir" with pre-created templates. Not only does this allow you to treat the cloned evennia repo as a proper library, you can also use the same evennia install for multiple games and makes it a lot clearer just what comes from us and what is your custom code.  
  
Below is a fun Gource representation (courtesy of Youtuber Landon Wilkins) of how the Evennia repository structure has changed over the years. You can see the latest library-change a little after the [3minute, 20 second mark](https://youtu.be/sXCm78XEJ9c?t=3m20s).  
  

## Typeclasses into proxies

At the same time as the library change, I also completely overhauled the way typeclasses are represented in Evennia: Typeclasses are Python classes that links back to a database model under the hood. They used to use a custom overloading of varioust get/set methods, now they instead utilize [django proxy models](https://docs.djangoproject.com/en/1.9/topics/db/models/#proxy-models) extended to support multiple inheritance. T  
  
his radically increased performance and made the code considerably cleaner, as well as completely hid the core django model from the end user (no longer a need to track if you were dealing with a model or its typeclass - you only ever run into typeclasses). This, together with the library-model led to some changes in people's source codes.  
  
Even so, this change led to a lot less problems and edge-cases than I had anticipated: it seems more people had issues with upgrading django than with adopting their codes to the new typeclass changes ...  
  

## Evennia Autodocs

Following the big library merger I sat down to write a more comprehensive autodoc utility. We had been distributing a Doxygen config file with the repo for a long time, but I wanted something that integrated with our github wiki, using markdown in the source (because frankly, while Sphinx produces very pretty output, ReST markup looks really ugly in source code, in my opinion).  
  
The result was the api2md program, which is now a part of our wiki repository. It allows our source code to be decorated in "Google style", very readable output:  
  
```python
def funcname(a, b, c, d=False):  """  
    This is a brief introduction to the
    function/class/method  
  
    Args:  
        a (str): This is a string argument that
          we can talk about over multiple lines.  
        b (int or str): Another argument  
        c (list): A list argument  
        d (bool, optional): An optional keyword argument  
  
    Returns:  
        str: The result of the function  
  
    Notes:  
        This is an example function. If `d=True`, something 
        amazing will happen.  
  
    """
```
  
This will be parsed and converted to a Markdown entry and put into the Github wiki, one page per module. The result is the automatically generated [Evennia API autodocs](https://github.com/evennia/evennia/wiki/evennia), reachable as any other wiki page.  
  
The convertion/prettification of all core functions of Evennia to actually _use_ the Google-style docstrings took almost all year, finishing late in autumn. But now almost all of Evennia uses this style. Coincidentally this also secures us at a 45% comment/code ratio. This places us in the top 10% of well-documented open-source projects according to [openhub](https://www.openhub.net/p/evennia/factoids#FactoidCommentsVeryHigh) (gotta love statistics).  
  

## Imaginary realities / Optional Realities

Spring of 2015 saw some more articles for the [Imaginary Realities](http://journal.imaginary-realities.com/) e-zine as well as some for the newly-opened [Optional Realities](http://optionalrealities.com/) web forum (unrelated, despite the similar name). The latter was made by a team working on a commercial Evennia-based sci-fi game, but the forums were open for other games (of any engine) and general discussion on mud and mud design.  
  
Optional Realities published an impressive range of articles (one every week for several months) and organized several very interesting mud-related contests. It did, I think, a lot for bringing some new life to the mud-development scene.  Unfortunately Optional Realities suffered a complete database loss towards the end of the year, forcing it to sort of reboot from scratch. I hope it will rebound and that the articles can be put back online again!  
  

## Ainneve

Over summer I put out a general roll call for developers willing to lead the development of a small but fully functioning Evennia demo game - a project separate from the main Evennia development. The idea is to have something working for people to rip out and start from. The response to my request was very good and we relatively quickly ended up with two devs willing to lead and direct the effort.  
  
The work-in-progress demo game they started is called _[Ainneve](https://github.com/evennia/ainneve)_. It uses the base [Open Adventure](http://geekguild.com/openadventure/) RPG rules and is distributed using the same liberal licence as Evennia.  
  
Ainneve has been sputtering along throughout autumn and winter, and while progress has been a bit ... sporadic, it seems to attract new volunteers to help out. As more of the base systems gets finalized there is going to be even more "low hanging fruit" for people to jump in and help with.  
  

## EvMenu, EvMore and EvEditor, RPSystem

In July I merged some new systems into Evennia's utilities library. _EvMenu_ is a class that builds an in-game menu. It uses multiple-choice questions for the user to navigate its nodes. I had a "menusystem" in our contrib/ folder since many years, but it was showing its age and when I found I myself didn't really understand how it was working I found it time to make something more flexible.  
  
The _EvMore_ is a page-scroller that allows the server to pause long texts and wait for the user to press a key before continuing. It's functionality is similar to the unix _more_ program.  
  
For its part, _EvEditor_ has existed for a while as well, but it was moved from the contrib folder into the main utilility library as it turned out to be an important and common resource (it's basically a mud-version of the classic _vi_ editor).  
  
Finally, some months later, in September, I added the _rpsystem_ and _rplanguage_ contribution modules. The former is an author-stance recognition system similar to what is seen in some rp-heavy muds (where you don't know/see people's name off the bat, but only their description, until you manually assign a name to them).  
  
The _rplanguage_ module is used for handling foreign (fantasy) languages by obfuscating words heard by different parties depending on their relative language skills.  
  

## Python 3 ... some day

As we know, Evennia uses Python 2. In autumn of 2015 first one and then two of our users took upon themselves to help make Evennia a little more ready for running also under Python 3. After a lot of work, Evennia's core is now using code syntax that is compatible with both Python 2 and 3.  
  
We _don't_ run under Python 3 at this point though. This is not something under our control, but is due to Twisted not supporting Python 3 yet. But when it becomes possible, we are now better prepared for transitioning to a point where we can (hopefully) support both main Python versions.  
  

## EvCast

In September, user whitenoise started his "EvCast" video tutorial series on Evennia. There are so far two episodes, one on installing Evennia and the second on general Python concepts you need to use Evennia efficiently:  

<iframe width="320" height="266" src="https://www.youtube.com/embed/tjiS2Bx5xb0" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
  

## `Python.__init__` Podcast

In the end of September I was interviewed by the hosts of the _python.__init___ podcast. Turned into more than an hour of discussion about Evennia. T'was fun! You can [listen to it here](https://plus.google.com/+Podcastinit-the-python-podcast/posts/Vu9dPVjsR9h).  
  

## Nested inlinefuncs

Towards the end of the year I got (via Optional Realities) lured to participate in another text-gaming related website, [musoapbox](http://musoapbox.net/). This is a forum primarily populated by players from the MUSH-side of text-gaming. After some back and forth they made a strong case for increasing the functionality of Evennia's _inlinefunctions_.  
  
An inlinefunction is, in Evennia, a function call embedded in a string sent to the server. This is parsed and executed (no, there is no dangerous eval happening, the call is parsed as text and then called as a normal function call). It allows for text to be dynamically replaced at run-time. What the MUSHers suggested was to also allow those inlinefunc's to be nestable - that is, to implement a call stack. The nestable form of inlinefuncs was merged with Evennia master at the end of November.  
  

## Patreon

This actually happened already back in February: after some requests for more ways to support Evennia development, I opened [a Patreon page](https://www.patreon.com/griatch?ty=h). And here at the end of the year, a whole ten patrons have signed up for it. Very encouraging!  
  

## Next year

In 2016 the first upcoming thing that comes to mind is push out the changes to the webclient infrastructure. That has been a long time coming since I've been unsure of how to proceed on it for quite some time. The goal is to make the webclient a lot more "pluggable" and modular than it is, and to clean up its API and way of communicating with the server. Overall I think the web-side of things need some love.  
  
I'll likely put together some more general-use contribs as well, I have some possibles in mind.   
  
We'll continue squashing bugs and work down our roadmap.  
  
I'll also try to get an Evennia Wikipedia.org page together, if you want to look at how it's progressing and help editing it, see the Evennia mailing list for the link.  
  
  
... And a lot more I don't know yet, no doubt! On towards a new year!