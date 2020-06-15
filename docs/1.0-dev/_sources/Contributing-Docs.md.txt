# Evennia docs

Documentation for the Evennia MUD creation system.

```warning::
    WARNING: This system is still WIP and many things are bound to change!
```

The live documentation is (or will in the future be) available at 
[https://evennia.github.io/evennia/latest](https://evennia.github.io/evennia/latest).

## Editing the docs

The documentation source files are `*.md` (Markdown) files found in `evennia/docs/source/`.
Markdown files are simple text files that can be edited with a normal text editor. They can also
contain raw HTML directives (but that is very rarely needed). They primarly use
the [Markdown][commonmark] syntax. See [the syntax section below](#Editing-syntax) for more help.

> Note: Don't edit the files in `source/api/`. These are auto-generated and your changes
> will be lost.

### Contributing to docs

Contributing to the docs is is like [contributing to the rest of Evennia][contributing]:
Check out the branch of Evennia you want to edit the documentation for. Create your
own work-branch, make your changes to files in `evennia/docs/source/` and make a PR for it!

## Building the docs locally

The sources in `evennia/docs/source/` are built into a pretty documentation using
the [Sphinx][sphinx] static generator system. To do so locally you need to either
use a system with `make` (Linux/Unix/Mac or [Windows-WSL][Windows-WSL]). Lacking that, you could
in principle also run the sphinx build-commands manually - read the `evennia/docs/Makefile` to see 
which commands are run by `make`.

You don't necessarily _have_ to build the docs locally to contribute.  But
building them allows you to check for yourself that syntax is correct and that
your change comes out looking as you expected.

### Building only the main documentation

If you only want to build the main documentation pages (not the API auto-docs),
you don't need to install Evennia itself, only the documentation resources.
All is done in your terminal/console.

- (Optional, but recommended): Activate a virtualenv with Python 3.7.
- `cd` to into the `evennia/docs` folder.
- Install the documentation-build requirements:

    ```
    make install
    or
    pip install -r requirements.txt
    ```

- Next, build the html-based documentation:

    ```
    make quick
    ```

- The html-based documentation will appear in the new
  folder `evennia/docs/build/html/`. Note any errors from files you have edited.
- Use a web browser to open `file://<path-to-folder>/evennia/docs/build/html/index.html` and view 
  the docs. Note that you will get errors if clicking a link to the auto-docs, because you didn't 
  build them!

### Building the main documentation and API docs

The full documentation includes both the doc pages and the API documentation
generated from the Evennia source. For this you must install Evennia and
initialize a new game with a default database (you don't need to have it
running)

- Follow the normal [Evennia Getting-Started instructions][getting-started]
  to install Evennia into a virtualenv. Get back here once everything is installed but
  before creating a new game.
- Make sure you `cd` to the folder _containing_ your `evennia/` repo (so two levels 
  up from `evennia/docs/`).
- Create a new game folder called exactly `gamedir` at the same level as your `evennia`
repo with

    ```
    evennia --init gamedir
    ```

- Then `cd` into it and create a new, empty database. You don't need to start the game
  or do any further changes.

    ```
    evennia migrate
    ```

- This is how the structure should look at this point:

    ```
      (top)
      |
      ----- evennia/  (the top-level folder, containing docs/)
      |
      ----- gamedir/
    ```

If you are already working on a game, you may of course have your 'real' game folder there as 
well. We won't touch that.

- Make sure you are still in your virtualenv, then go to `evennia/docs/` and
  install the doc-building requirements:

    ```
    make install
    or
    pip install -r requirements.txt
    ```

- Finally, build the full documentation, including the auto-docs:

    ```
    make local
    ```

- The rendered files will appear in a new folder `evennia/docs/build/html/`.
  Note any errors from files you have edited.
- Point your web browser to `file://<path-to-folder>/evennia/docs/build/html/index.html` to 
  view the full docs.

#### Building with another gamedir

If you for some reason want to use another location of your `gamedir/`, or want it
named something else (maybe you already use the name 'gamedir' for your development ...),
you can do so by setting the `EVGAMEDIR` environment variable to the absolute path
of your alternative game dir. For example:

```
EVGAMEDIR=/my/path/to/mygamedir make local
```

### Building for release

The full Evennia documentation contains docs from many Evennia
versions, old and new. This is done by pulling documentation from Evennia's old release
branches and building them all so readers can choose which one to view. Only
specific official Evennia branches will be built, so you can't use this to
build your own testing branch.

- All local changes must have been committed to git first, since the versioned
docs are built by looking at the git tree.
- To build for local checking, run (`mv` stands for "multi-version"):

    ```
    make mv-local
    ```

This is as close to the 'real' version as you can get locally. The different versions
will be found under `evennia/docs/build`. During deploy a symlink `latest` will point 
to the latest version of the docs.

#### Release 

Releasing the official docs requires git-push access the the Evennia `gh-pages` branch
on `github`. So there is no risk of you releasing your local changes accidentally.

- To deploy docs in two steps

    ```
    make mv-local
    make deploy
    ```

- If you know what you are doing you can also do build + deploy in one step:

     ```
     make release
     ```

After deployment finishes, the updated live documentation will be
available at https://evennia.github.io/evennia/latest/.

# Editing syntax

The format used for Evennia's docs is [Markdown][commonmark-help] (Commonmark). While markdown supports a 
few alternative forms for some of these, we try to stick to the below forms for consistency.

### Italic/Bold 

We generally use underscores for italics and double-asterisks for bold:

- `_Italic text_` - _Italic text_
- `**Bold Text**` - **Bold text**

### Headings 

We use `#` to indicate sections/headings. The more `#` the more of a sub-heading it is (will get smaller
and smaller font).

- `# Heading`
- `## SubHeading`
- `## SubSubHeading` 

> Don't reuse the same heading/subheading name over and over in the same document. While Markdown does not prevent
it, it makes it impossible to link to those duplicates properly (see next section). 

### Lists 

One can create both bullet-point lists and numbered lists:

```
- first bulletpoint
- second bulletpoint
- third bulletpoint
```

- first bulletpoint
- second bulletpoint
- third bulletpoint

```
1. Numbered point one
2. Numbered point two
3. Numbered point three
```

1. Numbered point one
2. Numbered point two
3. Numbered point three

### Notes 

A note can be used to enphasise important things. It's added by starting one or more lines with `>`.

```
> Note: This is an important 
> thing to remember.  
```

> Note: This is an important 
> thing to remember.  

### Links 

- `[linktext](url_or_ref)` - gives a clickable link [linktext][linkdemo]. 

The `url_or_ref` can either be a full `http://...` url or an internal _reference_. For example, use
`[my document](My-Document)` to link to the document `evennia/docs/source/My-Document.md`. Avoid using 
full `http://` linking unless really referring to an external resource.

- `[linktext](ref#heading-name)`

You can point to sub-sections (headings) in a document by using a single `#` and the name of the 
heading, replacing spaces with dashes. So to refer to a heading `## Cool Stuff` inside `My-Document`
would be a link `[cool stuff](My-Document#Cool-Stuff)`.

- `[linktext][linkref]` - refer to a reference defined later in the document.

Urls can get long and if you are using the same url in many places it can get a little cluttered. So you can also put 
the url as a 'footnote' at the end of your document
and refer to it by putting your reference within square brackets `[ ]`. Here's an example: 

```
This is a [clickable link][mylink]. This is [another link][1].

...


[mylink]: http://...
[1]: My-Document

```

#### Special references 

The Evennia documentation supports some special reference shortcuts in links:

##### Github online repository

- `github:` - a shortcut for the full path to the Evennia repository on github. This will refer to
  the `master` branch by default:
  
        [link to objects.py](github:evennia/objects/objects.py)

    This will remap to https://github.com/evennia/evennia/blob/master/evennia/objects/objects.py.
- To refer to the `develop` branch, start the url with `develop/`: 

        [link to objects.py](github:develop/evennia/objects/objects.py)

##### API

- `api:` - references a path in the api documentation. This is specified as a Python-path:

        [link to api for objects.py](api:evennia.objects)

    This will create a link to the auto-generated `evennia/source/api/evennia.objects.rst` document. 

    Since api-docs are generated alongside the documentation, this will always be the api docs for the
    current version/branch of the docs. 

##### Bug reports/feature request


- `issue`, `bug-report`, `feature-request` - links to the same github issue select page. 

        If you find a problem, make a [bug report](issue)!

    This will generate a link to https://github.com/evennia/evennia/issues/new/choose.
    
 > For some reason these particular shortcuts gives a warning during documentation compilation. This 
 > can be ignored. 

### Verbatim text

It's common to want to mark something to be displayed verbatim - just as written - without any 
Markdown parsing. In running text, this is done using backticks (\`), like \`verbatim text\` becomes `verbatim text`. 

If you want to put the verbatim text on its own line, you can do so easily by simply indenting
it 4 spaces (add empty lines on each side for readability too): 

```
This is normal text 

    This is verbatim text 

This is normal text 
```

Another way is to use triple-backticks:

````
```
Everything within these backticks will be verbatim.

```
````

### Code blocks

A special case is code examples - we want them to get code-highlighting for readability. This is done by using 
the triple-backticks and specify which language we use:

````
```python

def a_python_func(x):
   return x * x 
    
``` 
````

```python

def a_python_func(x):
   return x * x 
    
``` 

### ReST blocks

Markdown is easy to read and use. But while it does most of what we need, there are some things it's 
not quite as expressive as it needs to be. For this we need to fall back to the [ReST][ReST] markup 
language which the documentation system uses under the hood. This is done by specifying `eval_rst` as 
the name of the `language` of a literal block: 

````
```eval_rst

    This will be evaluated as ReST. 

```
````
There is also a short-hand form for starting a [ReST directive][ReST-directives] without need for `eval_rst`:

````
```directive:: possible-option
  
  Content that *must* be indented for it to be included in the directive.

  New lines are ignored except if separated by an empty line.
```
````

See below for examples of this.

#### Note

This kind of note may pop even more than a normal `> note`. It may however also make the test
feel more 'busy', so use with care.

````
```note::

  Remember that ...

```
````
```note::

  Remember that ...

```

#### Important

This is for particularly important and visible notes. 

````
```important:: 
  This is important because it is!
```

````
```important:: 
  This is important because it is!
```

#### Warning

A warning block is used to draw attention to particularly dangerous things, or features easy to 
mess up.

````
```warning::
  Be careful about this ... 
```
````

```warning::
  Be careful about this ... 
```

#### Version changes and deprecations

These will show up as one-line warnings that suggest an added, changed or deprecated 
feature beginning with particular version.

````
```versionadded:: 1.0
```
````

```versionadded:: 1.0
```

````
```versionchanged:: 1.0
  How the feature changed with this version.
```
````

```versionchanged:: 1.0
  How the feature changed with this version.
```

````
```deprecated:: 1.0
```
````

```deprecated:: 1.0
```

#### Sidebar 

This will display an informative sidebar that floats to the side of regular content. This is useful
for example to remind the reader of some concept relevant to the text.

````
```sidebar:: Things to remember

  - There can be bullet lists
  - in here.

  Headers:
    with indented blocks like this 
  Will end up: 
    as full sub-headings in the sidebar.
```
````

```sidebar:: Things to remember

  - There can be bullet lists
  - in here.

  Headers:
    with indented blocks like this 
  Will end up:
    as full sub-headings in the sidebar.
```
Remember that for ReST-directives, the content within the triple-backticks _must_ be indented to 
some degree or the content will just appear outside of the directive as regular text. 

If wanting to make sure to have the next header appear on a row of its own, one can embed 
a plain HTML string in the markdown like so: 

```html
<div style="clear: right;"></div>
```

<div style="clear: right;"></div>

#### Tables 

A table is specified using [ReST table syntax][ReST-tables]:

````
```eval_rst

=====  =====  =======
A      B      A and B
=====  =====  =======
False  False  False
True   False  False
False  True   False
True   True   True
=====  =====  =======
```
````

```eval_rst

=====  =====  =======
A      B      A and B
=====  =====  =======
False  False  False
True   False  False
False  True   False
True   True   True
=====  =====  =======
```

or the more flexible but verbose

````
```eval_rst
+------------------------+------------+----------+----------+
| Header row, column 3   | Header 2   | Header 3 | Header 4 |
| (header rows optional) |            |          |          |
+========================+============+==========+==========+
| body row 1, column 1   | column 2   | column 3 | column 4 |
+------------------------+------------+----------+----------+
| body row 2             | ...        | ...      |          |
+------------------------+------------+----------+----------+
```
````

```eval_rst
+------------------------+------------+----------+----------+
| Header row, column 3   | Header 2   | Header 3 | Header 4 |
| (header rows optional) |            |          |          |
+========================+============+==========+==========+
| body row 1, column 1   | column 2   | column 3 | column 4 |
+------------------------+------------+----------+----------+
| body row 2             | ...        | ...      |          |
+------------------------+------------+----------+----------+
```

#### A more flexible code block 

The regular Markdown codeblock is usually enough but for more direct control over the style, one 
can also specify the code block explicitly in `ReST`.
for more flexibility. It also provides a link to the code block, identified by its name.


````
```code-block:: python
    :linenos:
    :emphasize-lines: 1-2,8
    :caption: An example code block
    :name: A full code block example

    from evennia import Command
    class CmdEcho(Command):
        """
        Usage: echo <arg>
        """
        key = "echo"
        def func(self):
            self.caller.msg(self.args.strip())
```
````

```code-block:: python
    :linenos:
    :emphasize-lines: 6-7,12
    :caption: An example code block
    :name: A full code block example

    from evennia import Command
    class CmdEcho(Command):
        """
        Usage: echo <arg>
        """
        key = "echo"
        def func(self):
            self.caller.msg(self.args.strip())
```
Here, `:linenos:` turns on line-numbers and `:emphasize-lines:` allows for emphasizing certain lines
in a different color. The `:caption:` shows an instructive text and `:name:` is used to reference this
block through the link that will appear (so it should be unique for a give document). 

> The default markdown syntax will actually generate a code-block ReST instruction like this 
> automatically for us behind the scenes. The automatic generation can't know things like emphasize-lines
> or caption since that's not a part of the Markdown specification.

# Technical

Evennia leverages [Sphinx][sphinx] with the [recommonmark][recommonmark] extension, which allows us to write our
docs in light-weight Markdown (more specifically [CommonMark][commonmark], like on github) rather than ReST.
The recommonmark extension however also allows us to use ReST selectively in the places were it is more
expressive than the simpler (but much easier) Markdown.

For [autodoc-generation][sphinx-autodoc] generation, we use the sphinx-[napoleon][sphinx-napoleon] extension
to understand our friendly Google-style docstrings used in classes and functions etc.



[sphinx]: https://www.sphinx-doc.org/en/master/
[recommonmark]: https://recommonmark.readthedocs.io/en/latest/index.html
[commonmark]: https://spec.commonmark.org/current/
[commonmark-help]: https://commonmark.org/help/
[sphinx-autodoc]: http://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#module-sphinx.ext.autodoc
[sphinx-napoleon]: http://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
[getting-started]: Getting-Started
[contributing]: Contributing
[ReST]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
[ReST-tables]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html#tables
[ReST-directives]: https://www.sphinx-doc.org/en/master/usage/restruturedtext/directives.html
[Windows-WSL]: https://docs.microsoft.com/en-us/windows/wsl/install-win10
[linkdemo]: #Links
