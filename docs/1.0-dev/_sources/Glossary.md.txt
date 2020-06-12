# Glossary


This explains common recurring terms used in the Evennia docs. It will be expanded as needed. 

- _[account](Glossary#account)_ - the player's account on the game
- _[admin-site](Glossary#admin-site)_ - the Django web page for manipulating the database
- _[attribute](Glossary#attribute)_ - persistent, custom data stored on typeclasses
- _[channel](Glossary#channel)_ - game communication channels
- _[character](Glossary#character)_ - the player's avatar in the game, controlled from _[account](Glossary#account)_
- _[core](Glossary#core)_ - a term used for the code distributed with Evennia proper
- _[django](Glossary#django)_ - web framework Evennia uses for database access and web integration
- _[field](Glossary#field)_ - a _[typeclass](Glossary#typeclass)_ property representing a database column
- _[git](Glossary#git)_ - the version-control system we use
- _[github](Glossary#github)_ - the online hosting of our source code
- _[migrate](Glossary#migrate)_ - updating the database schema
- _[multisession mode`](#multisession-mode)_ - a setting defining how users connect to Evennia
- _[object](Glossary#object)_ - Python instance, general term or in-game _[typeclass](Glossary#typeclass)_
- _[pip](Glossary#pip)_ - the Python installer
- _player_ - the human connecting to the game with their client
- _[puppet](Glossary#puppet)_ - when an [account](Glossary#account) controls an in-game [object](Glossary#object)
- _[property](Glossary#property)_ - a python property
- _evenv_ - see _[virtualenv](Glossary#virtualenv)_
- _[repository](Glossary#repository)_ - a store of source code + source history
- _[script](Glossary#script)_ - a building block for custom storage, systems and time-keepint
- _[session](Glossary#session)_ - represents one client connection
- _[ticker](Glossary#ticker)_ - Allows to run events on a steady 'tick'
- _[twisted](Glossary#twisted)_ - networking engine responsible for Evennia's event loop and communications
- _[typeclass](Glossary#typeclass)_ - Evennia's database-connected Python class
- _upstream_ - see _[github](Glossary#github)_
- _[virtualenv](Glossary#virtualenv)_ - a Python program and way to make an isolated Python install


---

### _account_

The term 'account' refers to the [player's](Glossary#player) unique account on the game. It is represented by the `Account` [typeclass](Glossary#typeclass) and holds things like email, password, configuration etc. 

When a player connects to the game, they connect to their account. The account has *no* representation in the game world. Through their Account they can instead choose to [puppet](Glossary#puppet) one (or more, depending on game mode) [Characters](Glossary#character) in the game. 

In the default [multisession mode](Sessions#multisession-mode) of Evennia, you immediately start puppeting a Character with the same name as your Account when you log in - mimicking how older servers used to work. 

### _admin-site_

This usually refers to [Django's](Glossary#django) *Admin site* or database-administration web page ([link to Django docs](https://docs.djangoproject.com/en/2.1/ref/contrib/admin/)). The admin site is an automatically generated web interface to the database (it can be customized extensively). It's reachable from the `admin` link on the default Evennia website you get with your server. 

### _attribute_

The term _Attribute_ should not be confused with ([properties](Glossary#property) or [fields](Glossary#field). The `Attribute` represents arbitrary pieces of data that can be attached to any [typeclassed](Glossary#typeclass) entity in Evennia. Attributes allows storing new persistent data on typeclasses without changing their underlying database schemas. [Read more about Attributes here](Attributes). 

### _channel_

A _Channel_ refers to an in-game communication channel. It's an entity that people subscribe to and which re-distributes messages between all subscribers. Such subscribers default to being [Accounts](Glossary#account), for out-of-game communication but could also be [Objects (usually Characters)](Glossary#character) if one wanted to adopt Channels for things like in-game walkie-talkies or phone systems. It is represented by the `Channel` typeclass. [You can read more about the comm system here](Communications#channels).

### _character_

The _Character_ is the term we use for the default avatar being [puppeted](Glossary#puppet) by the [account](Glossary#account) in the game world. It is represented by the `Character` typeclass (which is a child of [Object](Glossary#object)). Many developers use children of this class to represent monsters and other NPCs. You can [read more about it here](Objects#subclasses-of-object).

### _django_

[Django](https://www.djangoproject.com/) is a professional and very popular Python web framework, similar to Rails for the Ruby language. It is one of Evennia's central library dependencies (the other one is [Twisted](Glossary#twisted)). Evennia uses Django for two main things - to map all database operations to Python and for structuring our web site.
 
Through Django, we can work with any supported database (SQlite3, Postgres, MySQL ...) using generic Python instead of database-specific SQL: A database table is represented in Django as a Python class (called a *model*). An Python instance of such a class represents a row in that table. 

There is usually no need to know the details of Django's database handling in order to use Evennia - it will handle most of the complexity for you under the hood using what we call [typeclasses](Glossary#typeclass). But should you need the power of Django you can always get it. Most commonly people want to use "raw" Django when doing more advanced/custom database queries than offered by Evennia's [default search functions](Tutorial-Searching-For-Objects). One will then need to read about Django's _querysets_. Querysets are Python method calls on a special form that lets you build complex queries. They get converted into optimized SQL queries under the hood, suitable for your current database. [Here is our tutorial/explanation of Django queries](Tutorial-Searching-For-Objects#queries-in-django).

> By the way, Django (and Evennia) does allow you to fall through and send raw SQL if you really want to. It's highly unlikely to be needed though; the Django database abstraction is very, very powerful.

The other aspect where Evennia uses Django is for web integration. On one end Django gives an infrastructure for wiring Python functions (called *views*) to URLs: the view/function is called when a user goes that URL in their browser, enters data into a form etc. The return is the web page to show. Django also offers templating with features such as being able to add special markers in HTML where it will insert the values of Python variables on the fly (like showing the current player count on the web page). [Here is one of our tutorials on wiring up such a web page](Add-a-simple-new-web-page). Django also comes with the [admin site](Glossary#admin-site), which automatically maps the database into a form accessible from a web browser. 

### _core_

This term is sometimes used to represent the main Evennia library code suite, *excluding* its [contrib](Glossary#contrib) directory. It can sometimes come up in code reviews, such as

> Evennia is game-agnostic but this feature is for a particular game genre. So it does not belong in core. Better make it a contrib. 

### _field_

A _field_ or _database field_ in Evennia refers to a [property](Glossary#property) on a [typeclass](Glossary#typeclass) directly linked to an underlying database column. Only a few fixed properties per typeclass are database fields but they are often tied to the core functionality of that base typeclass (for example [Objects](Glossary#object) store its location as a field). In all other cases, [attributes](Glossary#attribute) are used to add new persistent data to the typeclass. [Read more about typeclass properties here](Typeclasses#about-typeclass-properties). 

### _git_

[Git](https://git-scm.com/) is a [version control](https://en.wikipedia.org/wiki/Version_control) tool. It allows us to track the development of the Evennia code by dividing it into units called *commits*. A 'commit' is sort of a save-spot - you save the current state of your code and can then come back to it later if later changes caused problems. By tracking commits we know what 'version' of the code we are currently using. 

Evennia's source code + its source history is jointly called a [repository](Glossary#repository). This is centrally stored at our online home on [GitHub](Glossary#github). Everyone using or developing Evennia makes a 'clone' of this repository  to their own computer - everyone automatically gets everything that is online, including all the code history. 

> Don't confuse Git and [GitHub](Glossary#github). The former is the version control system. The latter is a website (run by a company) that allows you to upload source code controlled by Git for others to see (among other things). 

Git allows multiple users from around the world to efficiently collaborate on Evennia's code: People can make local commits on their cloned code. The commits they do can then be uploaded to GitHub and reviewed by the Evennia lead devs - and if the changes look ok they can be safely *merged* into the central Evennia code - and everyone can *pull* those changes to update their local copies. 

Developers using Evennia often uses Git on their own games in the same way - to track their changes and to help collaboration with team mates. This is done completely independently of Evennia's Git usage. 

Common usage (for non-Evennia developers): 
- `git clone <github-url>` - clone an online repository to your computer. This is what you do when you 'download' Evennia. You only need to do this once. 
- `git pull` (inside local copy of repository) - sync your local repository with what is online.

> Full usage of Git is way beyond the scope of this glossary. See [Tutorial - version control](Version-Control) for more info and links to the Git documentation.

### _migrate_

This term is used for upgrading the database structure (it's _schema_ )to a new version. Most often this is due to Evennia's [upstream](Glossary#github) schema changing. When that happens you need to migrate that schema to the new version as well. Once you have used [git](Glossary#git) to pull the latest changes, just `cd` into your game dir and run

    evennia migrate 

That should be it (see [virtualenv](Glossary#virtualenv) if you get a warning that the `evennia` command is not available). See also [Updating your game](Updating-Your-Game) for more details. 

> Technically, migrations are shipped as little Python snippets of code that explains which database actions must be taken to upgrade from one version of the schema to the next. When you run the command above, those snippets are run in sequence. 

### _multisession mode_

This term refers to the `MULTISESSION_MODE` setting, which has a value of 0 to 3. The mode alters how players can connect to the game, such as how many Sessions a player can start with one account and how many Characters they can control at the same time. It is [described in detail here](Sessions#multisession-mode).

### _github_

[Github](https://github.com/evennia) is where Evennia's source code and documentation is hosted. This online [repository](Glossary#repository) of code we also sometimes refer to as _upstream_. 

GitHub is a business, offering free hosting to Open-source projects like Evennia. Despite the similarity in name, don't confuse GitHub the website with [Git](Glossary#git), the versioning system. Github hosts Git [repositories](Glossary#repository) online and helps with collaboration and infrastructure. Git itself is a separate project.

### _object_

In general Python (and other [object-oriented languages](https://en.wikipedia.org/wiki/Object-oriented_programming)), an `object` is what we call the instance of a *class*. But one of Evennia's core [typeclasses](Glossary#typeclasss) is also called "Object". To separate these in the docs we try to use `object` to refer to the general term and capitalized `Object` when we refer to the typeclass. 

The `Object` is a typeclass that represents all *in-game* entities, including [Characters](Glossary#character), rooms, trees, weapons etc. [Read more about Objects here](Objects). 

### _pip_

_[pip](https://pypi.org/project/pip/)_ comes with Python and is the main tool for installing third-party Python packages from the web. Once a python package is installed you can do `import <packagename>` in your Python code.

Common usage:
- `pip install <package-name>` - install the given package along with all its dependencies.
- `pip search <name>` - search Python's central package repository [PyPi](https://pypi.org/) for a package of that name.
- `pip install --upgrade <package_name>` - upgrade a package you already have to the latest version.
- `pip install <packagename>==1.5` - install exactly a specific package version.
- `pip install <folder>` - install a Python package you have downloaded earlier (or cloned using git).
- `pip install -e <folder>` - install a local package by just making a soft link to the folder. This means that if the code in `<folder>` changes, the installed Python package is immediately updated. If not using `-e`, one would need to run `pip install --upgrade <folder>` every time to make the changes available when you import this package into your code. Evennia is installed this way. 

For development, `pip` is usually used together with a [virtualenv](Glossary#virtualenv) to install all packages and dependencies needed for a project in one, isolated location on the hard drive. 

### _puppet_

An [account](Glossary#account) can take control and "play as" any [Object](Glossary#object). When doing so, we call this _puppeting_, (like [puppeteering](https://en.wikipedia.org/wiki/Puppeteer)). Normally the entity being puppeted is of the [Character](Glossary#character) subclass but it does not have to be. 

### _property_

A _property_ is a general term used for properties on any Python object. The term also sometimes refers to the `property` built-in function of Python ([read more here](https://www.python-course.eu/python3_properties.php)). Note the distinction between properties, [fields](Glossary#field) and [Attributes](Glossary#attribute).

### _repository_

A _repository_ is a version control/[git](Glossary#git) term. It represents a folder containing source code plus its versioning history. 

> In Git's case, that history is stored in a hidden folder `.git`. If you ever feel the need to look into this folder you probably already know enough Git to know why. 

The `evennia` folder you download from us with `git clone` is a repository. The code on [GitHub](Glossary#github) is often referred to as the 'online repository' (or the _upstream_ repository). If you put your game dir under version control, that of course becomes a repository as well. 

### _script_

When we refer to _Scripts_, we generally refer to the `Script` [typeclass](Typeclasses). Scripts are the mavericks of Evennia - they are like [Objects](Glossary#object) but without any in-game existence. They are useful as custom places to store data but also as building blocks in persistent game systems. Since the can be initialized with timing capabilities they can also be used for long-time persistent time keeping (for fast updates other types of timers may be better though). [Read more about Scripts here](Scripts)

### _session_

A [Session](Sessions) is a Python object representing a single client connection to the server. A given human player could connect to the game from different clients and each would get a Session (even if you did not allow them to actually log in and get access to an [account](Glossary#account)). 

Sessions are _not_ [typeclassed](Glossary#typeclass) and has no database persistence. But since they always exist (also when not logged in), they share some common functionality with typeclasses that can be useful for certain game states.

### _ticker_

The [Ticker handler](TickerHandler) runs Evennia's optional 'ticker' system. In other engines, such as [DIKU](https://en.wikipedia.org/wiki/DikuMUD), all game events are processed only at specific intervals called 'ticks'. Evennia has no such technical limitation (events are processed whenever needed) but using a fixed tick can still be useful for certain types of game systems, like combat. Ticker Handler allows you to emulate any number of tick rates (not just one) and subscribe actions to be called when those ticks come around.

### _typeclass_

The [typeclass](Typeclasses) is an Evennia-specific term. A typeclass allows developers to work with database-persistent objects as if they were normal Python objects. It makes use of specific [Django](Glossary#django) features to link a Python class to a database table. Sometimes we refer to such code entities as _being typeclassed_. 

Evennia's main typeclasses are [Account](Glossary#account), [Object](Glossary#object), [Script](Glossary#script) and [Channel](Glossary#channel).  Children of the base class (such as [Character](Glossary#character)) will use the same database table as the parent, but can have vastly different Python capabilities (and persistent features through [Attributes](Glossary#attributes) and [Tags](Glossary#tags). A typeclass can be coded and treated pretty much like any other Python class except it must inherit (at any distance) from one of the base typeclasses. Also, creating a new instance of a typeclass will add a new row to the database table to which it is linked. 

The [core](Glossary#core) typeclasses in the Evennia library are all named `DefaultAccount`, `DefaultObject` etc. When you initialize your [game dir] you automatically get empty children of these, called `Account`, `Object` etc that you can start working with. 

### _twisted_

[Twisted](https://twistedmatrix.com/trac/) is a heavy-duty asynchronous networking engine. It is one of Evennia's two major library dependencies (the other one is [Django](Glossary#django)). Twisted is what "runs" Evennia - it handles Evennia's event loop. Twisted also has the building blocks we need to construct network protocols and communicate with the outside world; such as our MUD-custom version of Telnet, Telnet+SSL, SSH, webclient-websockets etc. Twisted also runs our integrated web server, serving the Django-based website for your game. 

### _virtualenv_

The standard [virtualenv](https://virtualenv.pypa.io/en/stable/) program comes with Python. It is used to isolate all Python packages needed by a given Python project into one folder (we call that folder `evenv` but it could be called anything). A package environment created this way is usually referred to as "a virtualenv". If you ever try to run the `evennia` program and get an error saying something like "the command 'evennia' is not available" - it's probably because your virtualenv is not 'active' yet (see below).

Usage: 
- `virtualenv <name>` - initialize a new virtualenv `<name>` in a new folder `<name>` in the current location. Called `evenv` in these docs.
- `virtualenv -p path/to/alternate/python_executable <name>` - create a virtualenv using another Python version than default.
- `source <folder_name>/bin/activate`(linux/mac) - activate the virtualenv in `<folder_name>`.
- `<folder_name>\Scripts\activate` (windows) 
- `deactivate` - turn off the currently activated virtualenv.

A virtualenv is 'activated' only for the console/terminal it was started in, but it's safe to activate the same virtualenv many times in different windows if you want. Once activated, all Python packages now installed with [pip](Glossary#pip) will install to `evenv` rather than to a global location like `/usr/local/bin` or `C:\Program Files`.

> Note that if you have root/admin access you *could* install Evennia globally just fine, without using a virtualenv. It's strongly discouraged and considered bad practice though. Experienced Python developers tend to rather create one new virtualenv per project they are working on, to keep the varying installs cleanly separated from one another. 

When you execute Python code within this activated virtualenv, *only* those packages installed within will be possible to `import` into your code. So if you installed a Python package globally on your computer, you'll need to install it again in your virtualenv.

> Virtualenvs *only* deal with Python programs/packages. Other programs on your computer couldn't care less if your virtualenv is active or not. So you could use `git` without the virtualenv being active, for example.

When your virtualenv is active you should see your console/terminal prompt change to 

    (evenv) ...

... or whatever name you gave the virtualenv when you initialized it. 

> We sometimes say that we are "in" the virtualenv when it's active. But just to be clear - you never have to actually `cd` into the `evenv` folder. You can activate it from anywhere and will still be considered "in" the virtualenv wherever you go until you `deactivate` or close the console/terminal. 

So, when do I *need* to activate my virtualenv? If the virtualenv is not active, none of the Python packages/programs you installed in it will be available to you. So at a minimum, *it needs to be activated whenever you want to use the `evennia` command* for any reason. 
