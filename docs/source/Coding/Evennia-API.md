# Evennia API


Evennia makes much of its programming tools available directly from the top-level `evennia` package.
This is often referred to as Evennia's "flat" [Application Programming
Interface](https://en.wikipedia.org/wiki/Application_programming_interface) (API). The flat API
tries to collect and bring the most commonly used resources to the front in a way where everything
is available at a glance (in a flat display), making it a good place to start to learn Evennia.

> Evennia's flat (and full) API can be perused through the auto-generated [API Library
refence](github:evennia).

A good, interactive way to explore the flat API is to use [IPython](http://ipython.org/), a more
flexible version of the default Python shell. Inside your virtual environment you can install
IPython simply by

    pip install ipython

Windows users should also install [PyReadline](http://ipython.org/pyreadline.html):

    pip install pyreadline

With IPython installed, go to your game directory and run

    evennia shell

This should give you the IPython shell automatically. Inside IPython
you then do

    import evennia

Followed by

    evennia.<TAB>

That is, write `evennia.` and press the TAB key. What pops up is the contents of the `evennia` top-
level package - in other words [the "flat" API](github:evennia#the-flat-api).

    evennia.DefaultObject?

Starting to write the name of an API entity and pressing `<TAB>` will auto-complete the name. Adding
a question mark (`?`) to its name will show you its documentation. Append `??` to get the actual
source code. This way you can quickly explore Evennia and see what is available.


## To remember when importing from `evennia`

Properties on the root of the `evennia` package are *not* modules in their own right. They are just
shortcut properties stored in the `evennia/__init__.py` module. That means that you cannot use dot-
notation to `import` nested module-names over `evennia`. The rule of thumb is that you cannot use
`import` for more than one level down. Hence you can do

```python
    import evennia
    print(evennia.default_cmds.CmdLook)
```

or import one level down

```python
    from evennia import default_cmds
    print(default_cmds.CmdLook)
```

but you *cannot* import two levels down

```python
     from evennia.default_cmds import CmdLook # error!
```

This will give you an `ImportError` telling you that the module `default_cmds` cannot be found -
this is becasue `default_cmds` is just a *variable* stored in `evennia.__init__.py`; this cannot be
imported from. If you really want full control over which level of package you import you can always
bypass the root package and import directly from from the real location. For example
`evennia.DefaultObject` is a shortcut to `evennia.objects.objects.DefaultObject`. Using this full
path will have the import mechanism work normally. See `evennia/__init__.py` to see where the
package imports from.