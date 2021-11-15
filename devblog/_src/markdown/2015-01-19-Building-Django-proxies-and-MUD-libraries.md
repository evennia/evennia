  
copyrights: Image: "Bibliothek St. Florian" by Original uploader was Stephan Brunker at de.wikipedia Later versions were uploaded by Luestling at de.wikipedia. - Originally from de.wikipedia; description page is/was here.. Licensed under CC BY-SA 3.0 via Wikimedia Commons - [link](http://commons.wikimedia.org/wiki/File:Bibliothek_St._Florian.jpg#mediaviewer/File:Bibliothek_St._Florian.jpg)

---

[![](https://lh5.googleusercontent.com/proxy/06dVvLrRNe-EqZJBbCF12T6O69WuNMoJpK1Vo_aIRTed86sKe49GhKvHrA_y02GuSOxzZQGojbU0YCyHQzqWXVJME8YUJd89A3IDqqCag5b_xnBXxNwwPlq4Mpd7a7JdNQ=s0-d)](http://upload.wikimedia.org/wikipedia/commons/5/5e/Bibliothek_St._Florian.jpg)

2015 is here and there is a lot of activity going on in Evennia's repository, mailing list and IRC channel right now, with plenty of people asking questions and starting to use the system to build online games.  
  
We get newcomers of all kinds, from experienced coders wanting to migrate from other code bases to newbies who are well versed in mudding but who aim to use Evennia for learning Python. At the moment the types of games planned or under development seems rather evenly distributed between RPI-style MUDs and MUSH games (maybe with a little dominance of MUSH) but there are also a couple of hack-and-slash concepts thrown into the mix. We also get some really wild concepts pitched to us now and then. What final games actually comes of it, who can tell, but people are certainly getting their MU*-creative urges scratched in greater numbers, which is a good sign.  
  
Since Christmas our _"devel"_ branch is visible online and is teeming with activity. So I thought I'd post an summary about it in this blog. The more detailed technical details for active developers can be found on Evennia's mailing list [here](https://groups.google.com/forum/#%21topic/evennia/6ug7m872GIk) (note that full docs are not yet written for devel-branch).  
  
## Django proxies for Typeclasses  
  
I have written about Evennia's Typeclass system before on this blog. It is basically a way to "decorate" Django database models with a second set of classes to allow Evennia developers to create any type of game entity without having to modify the database schema. It does so by connecting one django model instance to one typeclass instance and overloading __setattr__ and __getattribute__ to transparently communicate between the two.  
  
For the devel branch I have refactored our typeclass system to make use of Django's _[proxy models](https://docs.djangoproject.com/en/dev/topics/db/models/#proxy-models)_ instead. Proxy models have existed for quite a while in Django, but they simply slipped under my radar until a user pointed them out to me late last year. A proxy model is basically a way to "replace the Python representation of a database table with a proxy class". Sounds like a Typeclass, doesn't it?  
Now, proxy models doesn't work _quite_ like typeclasses out of the box - for one thing if you query for them in the database you will get back the original model and not the proxy one. They also do not allow multiple inheritance. Finally I don't want Evennia users to have to set up django Meta info every time they use a proxy. So most work went into overloading the proxy multiclass inheritance check (there is a django issue about how to fix this). Along the way I also redefined the default managers and __init__ methods to always load the proxy actually searched for and not the model. I finally created metaclasses to handle all the boilerplate. We choose to keep the name _Typeclass_ also for this extended proxy. This is partly for legacy reasons, but typeclasses do have their own identity: they are not vanilla Django-proxies nor completely normal Python classes (although they are very close to the latter from the perspective of the end user).  
Since typeclasses now are directly inheriting from the base class (due to meta-classing this looks like normal Python inheritance), it makes things a lot easier to visualize, explain and use. Performance-wise this system is en par with the old, or maybe a little faster, but it will also be a lot more straight forward to cache than the old. I have done preliminary testing with threading and it looks promising (but more on that in a future post).   
  
  
## Evennia as a Python library package  
Evennia has until now been solely distributed as a version controlled source tree (first under SVN, then Mercurial and now via GIT and Github). In its current inception you clone the tree and find inside it a game/ directory where you create your game. A problem we have when helping newbies is that we can't easily put pre-filled templates in there - if people used them there might be merge conflicts when we update the templates upstream. So the way people configure Evennia is to make copies of template modules and then change the settings to point to that copy rather than the default module. This works well but it means a higher threshold of setup for new users and a lot of describing text. Also, while learning GIT is a useful skill, it's another hurdle to get past for those who just want to change something minor to see if Evennia is for them.  
  
In the devel branch, Evennia is now a library. The game/ folder is no longer distributed as part of the repository but is created dynamically by using the new binary evennia launcher program, which is also responsible for creating (or migrating) the database as well as operating the server:  
  
```
evennia --init mygame  
cd mygame  
evennia migrate  
evennia start
```

  
Since this new folder is _not_ under our source tree, we can set up and copy pre-made template modules to it that people can just immediately start filling in without worrying about merge conflicts. We can also dynamically create a setting file that fits the environment as well as set up a correct tree for overloading web functionality and so on. It also makes it a lot easier for people wanting to create multiple games and to put their work under separate version control.  
  
Rather than traversing the repository structure as before you henceforth will just do import evennia in your code to have access to the entirety of the API. And finally this means it will (eventually) be possible to install Evennia from [pypi](https://pypi.python.org/pypi/Evennia-MUD-Server/Beta) with something like pip install evennia. This will greatly ease the first steps for those not keen on learning GIT.  
  
## For existing users  
  
Both the typeclasses-as-proxies and the evennia library changes are now live in the devel branch. Some brave users have already started taking it through its paces (and is helping to flesh it out) but it will take some time before it merges into master.  
  
The interesting thing is that despite all this sounding like a huge change to Evennia, the coding API doesn't change very much, the database schema almost not at all. With the exception of some properties specific to the old connection between the typeclass and model, code translate over pretty much without change from the developer's standpoint.  
  
The main translation work for existing developers lies in copying over their code from the old game/ directory to the new dynamically created game folder. They need to do a search-and-replace so that they import from evennia rather than from src or ev. There may possibly be some other minor things. But so far testers have not found it too cumbersome or time consuming to do. And all agree that the new structure is worth it.  
  
So, onward into 2015!  
  
