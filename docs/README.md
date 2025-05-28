# Evennia docs

Documentation for the Evennia MUD creation system.

> WARNING: This system is still WIP and many things are bound to change!
> Contributing is still primarily to be done in the wiki.

The live documentation is available at `https://www.evennia.com/docs/latest/index.html/`.

# Editing the docs

The documentation source files are `*.md` (Markdown) files found in `evennia/docs/source/`.
Markdown files are simple text files that can be edited with a normal text editor. They primarily use
the [Markdown][commonmark] syntax. See [the syntax section below](#Editing-syntax) for more help.

Don't edit the files in `source/api/`. These are auto-generated and your changes
will be lost.

## Contributing

Contributing to the docs is like [contributing to the rest of Evennia][contributing]:
Check out the branch of Evennia you want to edit the documentation for. Create your
own work-branch, make your changes to files in `evennia/docs/source/` and make a PR for it!

# Building the docs locally

The sources in `evennia/docs/source/` are built into a pretty documentation using
the [Sphinx][sphinx] static generator system. To do so locally you need to either
use a system with `make` (Linux/Unix/Mac or [Windows-WSL][Windows-WSL]). Lacking that, you could
in principle also run the sphinx build-commands manually - read the `evennia/docs/Makefile` to see
which commands are run by `make`.

You don't necessarily _have_ to build the docs locally to contribute, but
building them allows you to check for yourself that syntax is correct and that
your change comes out looking as you expected.

## Building only the main documentation

If you only want to build the main documentation pages (not the API autodocs),
you don't need to install Evennia itself, only the documentation resources.
This action is done in your terminal/console.

- (Optional, but recommended): Activate a virtualenv with Python 3.7.
- `cd` to into the `evennia/docs` folder (where this README is).
- Install the documentation-build requirements:

    ```
    make install
    or
    pip install -r requirements.txt
    ```

- Next, build the html-based documentation.

    ```
    make quick
    ```

- The html-based documentation will appear in the new
  folder `evennia/docs/build/html/`. Note any errors from files you have edited.
- Use a web browser to open `evennia/docs/build/html/index.html` and view the docs.
  Note that you will get errors if clicking a link to the auto-docs, because you didn't build them!

## Building the main documentation and API docs

The full documentation includes both the doc pages and the API documentation
generated from the Evennia source. To build the full documentation you must install Evennia and
initialize a new game with a default database (you don't need to have it
running).

- Follow the normal [Evennia Getting-Started instructions][getting-started]
  to install Evennia. Use a virtualenv.
- Make sure you `cd` to the folder _containing_ your `evennia/` repo (so two levels up from `docs/`).
- Create a new game folder called `gamedir` at the same level as your `evennia`
repo with

    ```
    evennia --init gamedir
    ```

- Then `cd` into it and create a new, empty database. You don't need to start the game
  or make any further changes.

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

- Make sure you are still in your virtualenv, then go to `evennia/docs/` and
  install the doc-building requirements:

    ```
    make install
    or
    pip install -r requirements.txt
    ```

- Finally, build the full documentation including the auto-docs:

    ```
    make local
    ```

- The rendered files will appear in a new folder `evennia/docs/build/html`.
  Note any errors from files you have edited.
- Point your web browser to `evennia/docs/build/html/index.html` to view the full docs.

### Building with another gamedir

If for some reason you want to use another location of your `gamedir/` or want it
named something else (maybe you already use the name 'gamedir' for your development ...)
you can do so by setting the `EVGAMEDIR` environment variable to the absolute path
of your alternative game dir. For example:

    ```
    EVGAMEDIR=/my/path/to/mygamedir make local
    ```
## Building for Different Languages

You can translate the source files located in `evennia/docs/source/` into different languages. 
Documentation source files for each language should be placed in the corresponding 
`evennia/docs/source_${SPHINX_LANGUAGE}/` directory. Here, ${SPHINX_LANGUAGE} should adhere to the
[ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes) standard.

For example, the source files for Simplified Chinese documentation should be located under the path 
`evennia/docs/source_zh_CN/`.

During compilation, you need to define the `SPHINX_LANGUAGE` environment variable to build the 
documentation for a specific language. For instance:

    ```
    SPHINX_LANGUAGE=zh_CN make local
    ```

Alternatively, you can run make with other environment variables, for example:

    ```
    EVGAMEDIR=../gamedir SPHINX_LANGUAGE=zh_CN make local
    ```

- The html-based documentation will appear in the new 
  folder `evennia/docs/build_${SPHINX_LANGUAGE}/html/`. Note any errors from files you have edited.

- Use a web browser to open `evennia/docs/build_${SPHINX_LANGUAGE}/html/index.html` to view the documentation.

## Building for release

The full Evennia documentation also tracks documentation from older Evennia
versions. This is done by pulling documentation from Evennia's old release
branches and building them all so readers can choose which one to view. Only
specific official Evennia branches will be built so you can't use this to
build your own testing branch.

- All local changes must have been committed to git first, since the versioned
docs are built by looking at the git tree.

- To build for local checking, run (`mv` stands for "multi-version"):

    ```
    make mv-local
    ```

- The different versions will be found under `evennia/docs/build/versions/`.
- If you have git-push access to the Evennia `gh-pages` branch on `github`, you
can now deploy.

    ```
    make deploy
    ```

- If you know what you are doing you can also do build + deploy in one step:

    ```
    make release
    ```

- After deployment finishes, the updated live documentation will be
available at `https://evennia.github.io/evennia/`.

# Editing syntax

The format is [Markdown][commonmark-help] (Commonmark). While markdown supports a few alternative
forms for some of these, we try to stick to the below forms for consistency.

## Italic/Bold

We generally use underscores for italics and double-asterisks for bold:

- `_Italic text_`
- `**Bold Text**`

## Headings

We use `#` to indicate sections/headings. The more `#` the more of a sub-heading it is (the font will be smaller
and smaller).

- `# Heading`
- `## SubHeading`
- `## SubSubHeading`

> Don't reuse the same heading/subheading name over and over in the same document. While Markdown does not prevent
it, it makes it impossible to link to those duplicates properly (see next section).

## Lists

One can create both bullet-point lists and numbered lists:

```markdown
- first bulletpoint
- second bulletpoint
- third bulletpoint
```
```markdown
1. Numbered point one
2. Numbered point two
3. Numbered point three
```

## Notes

A note can be used to enphasise important things. It's added by starting one or more lines with `>`.

```
> Note: This is an important
> thing to remember.
```

## Links

- `[linktext](url_or_ref)` - gives a clickable link `linktext`.

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

### Special references

The Evennia documentation supports some special reference shortcuts in links:

#### Github online repository

- `github:` - a shortcut for the full path to the Evennia repository on github. This will refer to
  the `main` branch by default:

        [link to objects.py](github:evennia/objects/objects.py)

    This will remap to https://github.com/evennia/evennia/blob/main/evennia/objects/objects.py.

#### API

- `api:` - references a path in the api documentation. This is specified as a Python-path:

        [link to api for objects.py](api:evennia.objects)

    This will create a link to the auto-generated `evennia/source/api/evennia.objects.rst` document.

    Since api-docs are generated alongside the documentation, this will always be the api docs for the
    current version/branch of the docs.

#### Bug reports/feature request


- `issue`, `bug-report`, `feature-request` - links to the same github issue select page.

        If you find a problem, make a [bug report](issue)!

    This will generate a link to https://github.com/evennia/evennia/issues/new/choose.

 > For some reason these particular shortcuts give a warning during documentation compilation. This warning
 > can be ignored.

## Verbatim text

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

## Code blocks

Code examples are a special case - we want them to get code-highlighting for readability. This is done by using
the triple-backticks and specifying the language we use:

````
```python

def a_python_func(x):
   return x * x

```
````

## ReST blocks

Markdown is easy to read and use, but it isn't as expressive as it needs to be for some things. For this we
need to fall back to the [ReST][ReST] markup language which the documentation system uses under the hood. This is
done by specifying `eval_rst` as the name of the `language` of a literal block:

````
```{eval_rst}

    This will be evaluated as ReST.

```
````

````

See below for examples of this.

#### Important

This will display a one-line note that will pop even more than a normal `> note`.

````
```{important}
This is important because it is!
```
````

#### Warning

A warning block is used to draw attention to particularly dangerous things or features that are easy to
mess up.

````
```{warning}
Be careful about this ...
````

#### Version changes and deprecations

These will show up as one-line warnings that suggest an added, changed or deprecated
feature beginning with the particular version.

````
```{versionadded} 1.0
```
````

````
```{versionchanged} 1.0
  How the feature changed with this version.
```
````
````
```{deprecated} 1.0
```
````


#### Sidebar

This will display an informative sidebar that floats to the side of regular content. This is useful
to remind the reader of some concept relevant to the text.

````
```{sidebar} Things to remember

- There can be bullet lists
- in here.

Headers with indented blocks:
  like this
Will end up as full sub-headings:
  in the sidebar.
```
````

> Remember that for ReST-directives, the content within the triple-backticks _must_ be indented to
>some degree or the content will just appear outside of the directive as regular text.

#### Tables

Tables are done using Markdown syntax

```
| A | B | A and B |
| --- | --- | --- |
| False | False |  False |
| True |  False | False |
| False |  True |  False |
| True  |  True |  True |
```

| A | B | A and B |
| --- | --- | --- |
| False | False |  False |
| True |  False | False |
| False |  True |  False |
| True  |  True |  True |


#### A more flexible code block

The regular Markdown codeblock is usually enough but for more direct control over the style, one
can also specify the code block explicitly in `ReST`.
for more flexibility. It also provides a link to the code block, identified by its name.


````
```{code-block} python
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
````

Here, `:linenos:` turns on line-numbers and `:emphasize-lines:` allows for emphasizing certain lines
in a different color. The `:caption:` shows an instructive text and `:name:` is used to reference this
block through the link that will appear (so it should be unique for a give document).

> The default markdown syntax will actually generate a code-block ReST instruction like this
> automatically for us behind the scenes. The automatic generation can't know things like emphasize-lines
> or caption since that's not a part of the Markdown specification.

# Technical

Evennia leverages [Sphinx][sphinx] with the [MyST][MyST] extension, which allows us to write our
docs in light-weight Markdown (more specifically [CommonMark][commonmark], like on github) rather than ReST.
The recommonmark extension however also allows us to use ReST selectively in the places were it is more
expressive than the simpler (but much easier) Markdown.

For [autodoc-generation][sphinx-autodoc] generation, we use the sphinx-[napoleon][sphinx-napoleon] extension
to understand our friendly Google-style docstrings used in classes and functions etc.



[sphinx]: https://www.sphinx-doc.org/en/master/
[MyST]: https://myst-parser.readthedocs.io/en/latest/syntax/reference.html
[commonmark]: https://spec.commonmark.org/current/
[commonmark-help]: https://commonmark.org/help/
[sphinx-autodoc]: https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#module-sphinx.ext.autodoc
[sphinx-napoleon]: https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
[getting-started]: https://github.com/evennia/evennia/wiki/Getting-Started
[contributing]: https://github.com/evennia/evennia/wiki/Contributing
[ReST]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
[ReST-tables]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html#tables
[ReST-directives]: https://www.sphinx-doc.org/en/master/usage/restruturedtext/directives.html
[Windows-WSL]: https://docs.microsoft.com/en-us/windows/wsl/install-win10
