copyrights: Beetle image: https://goodfreephotos.com (public domain)

---

[![](https://1.bp.blogspot.com/-Ez3s-a2ja-8/XZIg4EA7wUI/AAAAAAAAK7I/rYyRh8tvpQkjRnd-VJe9AUzI9g4ZwKb9wCLcBGAsYHQ/s320/black-beetle-on-concrete_800.jpg)](https://1.bp.blogspot.com/-Ez3s-a2ja-8/XZIg4EA7wUI/AAAAAAAAK7I/rYyRh8tvpQkjRnd-VJe9AUzI9g4ZwKb9wCLcBGAsYHQ/s1600/black-beetle-on-concrete_800.jpg)

Since [version 0.9](http://evennia.blogspot.com/2019/07/evennia-09-released.html) of [Evennia](http://www.evennia.com/), the MU*-creation framework, was released, work has mainly been focused on bug fixing. But there few new features also already sneaked into master branch, despite technically being changes slated for Evennia 1.0.  
  
  
  
  
## On Frontends  
  
Contributor friarzen has chipped away at improving Evennia's HTML5 web client. It already had the ability to structure and spawn any number of nested text panes. In the future we want to extend the user's ability to save an restore its layouts and allow developers to offer pre-prepared layouts for their games. Already now though, it has gotten plugins for handling both graphics, sounds and video:  
  

 [![](https://1.bp.blogspot.com/-pd6LQR70OkU/XZIaSIo__6I/AAAAAAAAK68/LoHgTq4xW58aHQvH-OHEqd7QfCcBUgZRgCLcBGAsYHQ/s400/Screenshot%2Bfrom%2B2019-09-30%2B17-06-58.png)](https://1.bp.blogspot.com/-pd6LQR70OkU/XZIaSIo__6I/AAAAAAAAK68/LoHgTq4xW58aHQvH-OHEqd7QfCcBUgZRgCLcBGAsYHQ/s1600/Screenshot%2Bfrom%2B2019-09-30%2B17-06-58.png) 

> _Inline image by me (deviantart.com/griatch-art)_

A related fun development is Castlelore Studios' development of an [Unreal Engine Evennia plugin](https://www.unrealengine.com/marketplace/en-US/slug/evennia-plugin) (this is unaffiliated with core Evennia development and I've not tried it, but it looks pretty nifty!): 

  

[![](https://cdn1.epicgames.com/ue/product/Screenshot/EvenniaPlugin1920x1080-2-1920x1080-4705074bbe9ecdc688a46880506eb419.png)](https://cdn1.epicgames.com/ue/product/Screenshot/EvenniaPlugin1920x1080-2-1920x1080-4705074bbe9ecdc688a46880506eb419.png)

> _Image ©Castlelore Studios_

## On Black  
  
Evennia's source code is extensively documented and was _sort of_ adhering to the Python formatting standard PEP8. But many places were sort of hit-and-miss and others were formatted with slight variations due to who wrote the code.  
   
After pre-work and recommendation by Greg Taylor, Evennia has adopted the [black autoformatter](https://pypi.org/project/black/) for its source code. I'm not really convinced that black produces the best output of all possible outputs every time, but as Greg puts it, it's at least consistent in style. We use a line width of 100.  
  
I have set it up so that whenever a new commit is added to the repo, the black formatter will run on it. It may still produce line widths >100 at times (especially for long strings), but otherwise this reduces the number of different PEP8 infractions in the code a lot.  
  
## On Python3  
  
Overall the move to Python3 appears to have been pretty uneventful for most users. I've not heard almost any complaints or requests for help with converting an existing game.  
The purely Python2-to-Python3 related bugs have been very limited after launch; almost all have been with unicode/bytes when sending data over the wire.  
  
People have wholeheartedly adopted the new f-strings though, and some spontaneous PRs have already been made towards converting some of Evennia existing code into using them.  
  
Post-launch we moved to Django 2.2.2, but the Django 2+ upgrades have been pretty uneventful so far.Some people had issues installing Twisted on Windows since there was no py3.7 binary wheel (causing them to have to compile it from scratch). The rise of the Linux Subsystem on Windows have alleviated most of this though and I've not seen any Windows install issues in a while.  

  

## On Future

  

For now we'll stay in bug-fixing mode, with the ocational new feature popping up here and there. In the future we'll move to the _develop_ branch again. I have a slew of things in mind for 1.0. 

  

Apart from bug fixing and cleaning up the API in several places, I plan to make use of the feedback received over the years to make Evennia a little more accessible for a new user. This means I'll also try reworking and consolidating the tutorials so one can follow them with a more coherent "red thread", as well as improving the documentation in various other ways to help newcomers with the common questions we hear a lot. 

  

The current project plan (subject to change) is [found here](https://github.com/evennia/evennia/projects/9). Lots of things to do!