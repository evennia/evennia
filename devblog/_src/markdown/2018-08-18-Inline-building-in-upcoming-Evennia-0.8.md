copyright: Building Image: Released as Creative Commons [here](https://en.wikipedia.org/wiki/File:Industrial_Trust_Building_Providence_RI.jpg)

---

[![](https://4.bp.blogspot.com/-h2OiulcCLIY/W3gLw-UzGgI/AAAAAAAAJKI/bS_gTmOcQoAgaGmCOnx-b4x60zTr1pVCgCLcBGAs/s200/773px-Industrial_Trust_Building_Providence_RI.jpg)](https://4.bp.blogspot.com/-h2OiulcCLIY/W3gLw-UzGgI/AAAAAAAAJKI/bS_gTmOcQoAgaGmCOnx-b4x60zTr1pVCgCLcBGAs/s1600/773px-Industrial_Trust_Building_Providence_RI.jpg)

  
[Evennia](http://www.evennia.com/), the Python MUD-server game development kit, is slowly creeping closer to its 0.8 release.  
  
In our development branch I've just pushed the first version of the new OLC (OnLine Creator) system. This is a system to allow builders (who may have limited coding knowledge) to customize and spawn new in-game objects more easily without code access. It's started with the **olc** command in-game. This is a visual system for manipulating Evennia _Prototypes_.  
  
  

### Briefly on Prototypes

The _Prototype_ is an Evennia concept that has been around a good while. The prototype is a Python dictionary that holds specific keys with values representing properties on a game object. Here's an example of a simple prototype:  
  
```
 {"key": "My house", 
  "typeclass": "typeclasses.houses.MyHouse"}
```
  
By passing this dict to the spawner, a new object named "My house" will be created. It will be set up with the given typeclass (a 'typeclass' is, in Evennia lingo, a Python class with a database backend). A prototype can specify all aspects of an in-game object - its attributes (like description and other game-specific properties), tags, aliases, location and so on. Prototypes also support inheritance - so you can expand on an existing template without having to add everything fresh every time.  
  
There are two main reasons for the Prototypes existing in Evennia:   

-   They allow you to customize _individual_ objects easier. For example you could have a 'Goblin' base prototype with inheriting prototypes  Goblin Wizard" and "Goblin Chieftain" - all using the same Typeclass, but with different Attributes, equipment etc. 
-   Prototypes can be manipulated and scripted by builders without needing full Python access. This means that while the Typeclasses are designed and supplied by the Python developer, the builders can then use that typeclass to make very different types of object instances in-game.

### What's new

As said, Prototypes have been around for a good while in Evennia. But in the past they were either manually entered directly as a dict on the command line, or created in code and read from a Python module. The former solution is cumbersome and requires that you know how to build a proper-syntax Python dictionary. The latter requires server code access, making them less useful to builders than they could be.  
  
_Note: If you are visually impaired, each image is also a link to a text-only version._  
  

[![OLC index](https://2.bp.blogspot.com/-ht9SIPcUxfc/W3f0xcl2HdI/AAAAAAAAJIk/VSk4VaBMhTc3J8ZaTnar9X2Rws-LOMiqACLcBGAs/s400/Screenshot%2Bfrom%2B2018-08-18%2B12-26-12.png "OLC index 1")](https://pastebin.com/raw/3YNtAdvz)

  
In Evennia 0.8, while you can still insert the Prototype as a raw dict, **spawn/menu** or the new **olc** command opens a new menu-driven interface.  
[![Select a prototype to load. This will replace any prototype currently being edited! ___________________________________________________________________________________________________  Select with <num>. Other actions: examine <num> | delete <num> Back (index) | Validate prototype | Quit   1: goblin_archer      5: goblin_archwizard                2: goblin_wizard                                          3: goblin                                                 4: archwizard_mixin            ](https://3.bp.blogspot.com/-tdauL-B6j1E/W3f01ltKlzI/AAAAAAAAJIs/Q5-cIY6AcGU_IXXasdzPWec7cxN061WrwCLcBGAs/s400/Screenshot%2Bfrom%2B2018-08-18%2B12-27-37.png "Prototype loading")](https://pastebin.com/raw/4UbUNGmG)

   
More importantly, builders can now create, save and load prototypes in the database for themselves and other builders to use. The prototypes can be tagged and searched as a joint resource. Builders can also lock prototypes if others are not to be able to read or use them to spawn things. Developers can still supply module-based "read-only" prototypes (for use as starting points or examples to their Builders, for example).  
  

[![Found 1 match.   (Warning: creating a prototype will overwrite the current prototype!) ____________________________________________________________________________________  Actions: examine <num> | create prototype from object <num> Back (index) | Quit   1: Griatch(#1)](https://2.bp.blogspot.com/-XFm3KqhLBwE/W3f93upyVLI/AAAAAAAAJJA/eZDWGPHM93MWvt2T5W8Ytr4cHstGg8iXACLcBGAs/s400/Screenshot%2Bfrom%2B2018-08-18%2B13-04-48.png "Load prototype from object")](https://pastebin.com/raw/dUGiSLDL)

  
You can now also use the menu to search for and create a new Prototype based on _an existing object_ (if you have access to do so). This makes it quick to start up a new prototype and tweak it for spawning other similar objects. Of course you could spawn temporary objects without saving the prototype as well.  
  

[![The Typeclass defines what 'type' of object this is - the actual working code to use.  All spawned objects must have a typeclass. If not given here, the typeclass must be set in one of the prototype's parents.  [No typeclass set] ______________________________________________________________________________________________________________________________________________  Back (prototype-parent) | Forward (key) | Index | Validate prototype | Quit   1: evennia.contrib.tutorial_world.mob.Mob                 7: evennia.contrib.tutorial_world.objects.TutorialObject    2: evennia.contrib.tutorial_world.objects.Climbable       8: evennia.contrib.tutorial_world.objects.Weapon            3: evennia.contrib.tutorial_world.objects.CrumblingWall   9: evennia.contrib.tutorial_world.objects.WeaponRack        4: evennia.contrib.tutorial_world.objects.LightSource     10: evennia.contrib.tutorial_world.rooms.BridgeRoom         5: evennia.contrib.tutorial_world.objects.Obelisk         current: (1/3)                                              6: evennia.contrib.tutorial_world.objects.Readable        next page ](https://1.bp.blogspot.com/-DYcYStEWXKk/W3f_-bnH4vI/AAAAAAAAJJY/iv4-GN8NTpUCpBvyXBwMUABG8TTPJYN9ACLcBGAs/s400/Screenshot%2Bfrom%2B2018-08-18%2B13-15-44.png "Typeclass selection, miltipage")](https://pastebin.com/raw/VspKN3xf)

  
Builders will likely not know which typeclasses are available in the code base. There are new a few ways to list them. The menu display makes use of Evennia 0.8's new EvMenu improvements, which allows for automatically creating multi-page listings (see example above).  
  
There is also a new switch to the **typeclass** command, **/list**, that will list all available typeclasses outside of the OLC.  

### Protfuncs

Another new feature are _Protfuncs._ Similarly to how _Inlinefuncs_ allows for calling for the result of a function call inside a text string, Protfuncs allows for calling functions inside a prototype's values. It's given on the form $funcname(arguments),  where arguments could themselves contain one or more nested Protfuncs.  
  
As with other such systems in Evennia, only Python functions in a specific module or modules (given by settings) are available for use as Protfuncs in-game. A bunch of default ones are included out of the box. Protfuncs are called at the time of spawning. So for example, you could set the Attribute   

> **Strength = $randint(5, 20)** 

to automatically spawn objects with a random strength between 5 and 20.  
  

[![prototype-key: goblin, -tags: [], -locks: spawn:all();edit:all() -desc: Built from goblin prototype-parent: None      key: goblin aliases: monster, mob attrs:  desc = You see nothing special.  strength = $randint(5,20)  agility = $random(6,20)  magic = 0 tags:  mob (category: None) locks:  call:true();control:id(1) or perm(Admin);delete:id(1) or perm(Admin);edit:perm(Admin);examine:perm(Builder);get:all();puppet:pperm(Developer) ;tell:perm(Admin);view:all() location: #2 home: #2   No validation errors found. (but errors could still happen at spawn-time) ______________________________________________________________________________________________________________________________________________  Actions: examine <num> | remove <num> Back (index) | Validate prototype | Quit   1: Spawn in prototype's defined location (#2)       2: Spawn in Griatch's location (Limbo)              3: Spawn in Griatch's inventory                     4: Update 2 existing objects with this prototype](https://1.bp.blogspot.com/-qHeRpEQTEzU/W3gFpJ9ge5I/AAAAAAAAJJw/-PVcelDk2CsIW1nJwWvMjazcJ9LyKx5pgCLcBGAs/s400/Screenshot%2Bfrom%2B2018-08-18%2B13-40-04.png "Spawning screen")](https://pastebin.com/raw/3VLMEPFd)

  
When spawning, the olc will validate the prototype and run tests on any Protfunc used. For convenience you can override the spawn-location if any is hard-coded in the prototype.  
  

[![https://pastebin.com/raw/K0a1z23h](https://4.bp.blogspot.com/-mkpUmXNQsWQ/W3gKE-5nnlI/AAAAAAAAJJ8/S65RiLXa6BcSstru3ePZmMna38cnWGRYQCLcBGAs/s400/Screenshot%2Bfrom%2B2018-08-18%2B13-58-27.png)](https://pastebin.com/raw/K0a1z23h)

  
The system will also allow you to try updating existing objects created from the same-named prototype earlier. It will sample the existing objects and calculate a 'diff' to apply. This is bit is still a bit iffy, with edge cases that still needs fixing.  

## Current status

The OLC is currently in the develop branch of Evennia - what will soon(ish) merge to become Evennia 0.8.  
  
It's a pretty big piece of code and as such it's still a bit unstable and there are edge cases and display issues to fix. But it would be great with more people trying it out and reporting errors so the childhood issues can be ironed out before release!