# VERSION WARNING

> This is the _experimental_ and _unstable_ documentation for the
> development branch of Evennia (v1.0-dev). It's based on converted docs
> from the [evennia wiki](https://github.com/evennia/evennia/wiki/) at
> 2020-06-12 22:36:53.  There are known conversion issues. This will
> slowly be ironed out as this is developed. 

> For now you are best off using the original wiki, or the less changing v0.9.1
> of these docs. You have been warned.

```sidebar:: An important sidebar

  - Extra features
  - Another feature 

  Third feature: 
    Stuff to do 

  Fourth feature:
    Even more.
```

# Evennia Documentation

This is the manual of [Evennia](http://www.evennia.com), the open source Python
`MU*` creation system. A link to the [feature-request](issue)

```note::

  This is a particular note.

```warning:: This is an important thing!
  Especially this.
```

```important:: This is an interesting thing!

  More text here!

  And here.
```

```seealso:: This is good to look at too.
  This in particular
```

```versionadded:: 1.0

  This feature was added here

```

```deprecated:: 1.0
  Use this thing instead.
```

```code-block:: python
     :emphasize-lines: 6-7,12
     :caption: An example code-block with everything turned on.
     :name: Full code-block example

     # Comment line
     from evennia import Command 

     class MyCommand(Command):
       """
       Usage: 
          cmd x
       """
       key = "cmd"

       def func(self):
         self.caller.msg(self.args)
```

```markdown
     # Comment line
     import System
     System.run_emphasis_line
     # Long lines in code blocks create a auto horizontal scrollbar
     System.exit!

```

<div style="clear: right;"></div>

There is [a lengthier introduction](Evennia-Introduction) to read. You might also want to read about
[how to get and give help](How-To-Get-And-Give-Help).

- The [Getting Started](Getting-Started) page helps installing and starting Evennia for the first time.
- The [Admin Docs](Administrative-Docs) covers running and maintaining an Evennia server.
- The [Builder Docs](Builder-Docs) helps for starting to build a game world using Evennia.
- The [Developer Central](Developer-Central) describes how Evennia works and is used by coders.
- The [Tutorials & Examples](Tutorials) contains help pages on a step-by-step or tutorial format.
- The [API](api:evennia) documentation is created from the latest source code.
- The [TOC](toc) lists all regular documentation pages.


[search]: https://www.google.com/cse/publicurl?cx=010440404980795145992:6ztkvqc46je
[group]: https://groups.google.com/forum/#%21forum/evennia
[chat]: http://tinyurl.com/p22oofg
[form]: http://tinyurl.com/c4tue23
[icon_new]: https://raw.githubusercontent.com/wiki/evennia/evennia/images/bright4.png
[icon_admin]: https://raw.githubusercontent.com/wiki/evennia/evennia/images/speedometer26.png
[icon_builder]: https://raw.githubusercontent.com/wiki/evennia/evennia/images/toolbox3.png
[icon_devel]: https://raw.githubusercontent.com/wiki/evennia/evennia/images/technical.png
[icon_tutorial]: https://raw.githubusercontent.com/wiki/evennia/evennia/images/living1.png
[icon_API]: https://raw.githubusercontent.com/wiki/evennia/evennia/images/python3.png
