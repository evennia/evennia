[![](https://4.bp.blogspot.com/-WXVxxb06XBA/UmZ_5TSzmrI/AAAAAAAACE4/NbBAjohOi6E/s1600/building-blocks.jpg)](https://4.bp.blogspot.com/-WXVxxb06XBA/UmZ_5TSzmrI/AAAAAAAACE4/NbBAjohOi6E/s1600/building-blocks.jpg)

Some Evennia updates.  
  
## Development
Lots of work has been happening in the [dev-clone](http://code.google.com/r/griatch-evennia-dev/source/list) of Evennia over the last few months.  
As alluded to in the last blog, the main work has been to move Evennia's webserver component into the _Server_-half of Evennia for various reasons, the most obvious one to make sure that all database writes happen in the same process, avoiding race conditions. But this move lead to a rework of the cache system, which in turn lead to me having to finalize the plans for how Out-of-Band protocols should be implemented server-side. And once that was finalized, OOB was pretty much implemented anyway. As part of making sure OOB trackers were updated correctly at all times meant reworking some of the ways data is stored ... So one thing led to another making this a bigger update than originally planned.  
  
I plan to make a more detailed post to the [mailing list](https://groups.google.com/forum/#!forum/evennia) soon with more technical details of the (relatively minor) API changes existing users should expect. The merging of the clone into the main repo is still a little way off, but adventurous users have already started testing things.  
  
## Google Code
I like Google Code. It's easy to manage and maintain, it has a good wiki and Issue system, not to mention that it allows the use of Mercurial. But in the beginning of September, suddenly all links to our user's clone repositories were _gone_ from the front of the project page_._ Not only that, creating new clones just didn't work anymore.  
Now any site can have bugs, and we made an [issue](http://code.google.com/p/support/issues/detail?id=30989) for it (other projects were similarly affected). But nothing happened for the longest time - at least two months given that we didn't report it right away. Just recently the functionality came back but there is no confirmation or comments from Google (our issue is not even closed).  
That such a fundamental feature can go unheeded for so long is disturbing to me, driving home the fact that Google is certainly not putting much priority in their code hosting.  
  
## Community
Some furious activity in the [IRC chat](http://webchat.freenode.net/?channels=evennia&uio=MT1mYWxzZSY5PXRydWUmMTE9MTk1JjEyPXRydWUbb) lately, with new people dropping in to chat and ask about Evennia. For example, an enthusiastic new user learned not only about Evennia but also Python for the first time. It was a lot of fun to see him go from having _no programming experience except_ _mush softcode_ to doing advanced Evennia system implementations in the course of a week and offering good feedback on new features in two. Good show! The freedom you get upgrading from something like softcode to Evennia's use of a full modern programming language was seemingly quite eye-opening.  
  
Other discussions have concerned the policies around using clones/branches for development as well as the benefits of some other hosting solution. Nothing has been decided on this. There is however now also an official GitHub mirror of Evennia's main repo to be found [here](https://github.com/Evennia/evennia).  
  
## Imaginary Realities
The deadline for entering articles for the _Imaginary Realities_ web zine [reboot](http://posted-stuff.blogspot.se/2013/10/imaginary-realities-update.html) has passed. It's a good initiative to bring this back - the [original (archived) webzine](http://en.wikipedia.org/wiki/Imaginary_Realities) remains a useful mud-creation resource to this day. I entered two articles, one about Evennia and another about general mud-roleplaying. It will be fun to see how it comes out, apparently the first issue will appear Nov 13