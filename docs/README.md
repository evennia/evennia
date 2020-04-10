# evennia-docs
Documentation for the Evennia MUD creation system.

> WARNING: This system is still WIP and many things are bound to change!
> Contributing is still primarily to be done in the wiki.

The live documentation is (will in the future be) available at `https://evennia.github.io/evennia/`.

# Editing the docs

The documentation source files are `*.md` (Markdown) files found in `evennia/docs/source/`.
Markdown files are simple text files that can be edited with a normal text editor. They use
the [Markdown][commonmark] syntax.

Don't edit the files in `source/api/`. These are auto-generated and your changes
will be lost.

See also later in this doc for [Help with editing syntax](#Help-with-editing-syntax).

## Contributing

Contributing to the docs is is like [contributing to the rest of Evennia][contributing]:
Check out the branch of Evennia you want to edit the documentation for. Create your
own work-branch, make your changes and make a PR for it!

# Building the docs

The sources in `evennia/docs/source/` are built into a pretty documentation using
the [Sphinx][sphinx] static generator system. To do so locally you need to either
use a system with `make` (Linux/Unix/Mac/Windows-WSL) or run sphinx-commands manually
(read the `Makefile` to see which commands are run by `make`).

You don't necessarily _have_ to build the docs locally to contribute.  But
building them allows you to check for yourself that syntax is correct and that
your change comes out looking as you expected.

## Building only the main documentation

If you only want to build the main documentation pages (not the API autodocs),
you don't need to install Evennia itself, only the documentation resources.
All is done in your terminal/console.

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
generated from the Evennia source. For this you must install Evennia and
initialize a new game with a default database (you don't need to have it
running)

- Follow the normal [Evennia Getting-Started instructions][getting-started]
  to install Evennia. Use a virtualenv.
- Make sure you `cd` to the folder _containing_ your `evennia/` repo (so two levels up from `docs/`).
- Create a new game folder called `gamedir` at the same level as your `evennia`
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

- The rendered files will appear in a new folder `evennia/docs/build/html`.
  Note any errors from files you have edited.
- Point your web browser to `evennia/docs/build/html/index.html` to view the full docs.

### Building with another gamedir

If you for some reason want to use another location of your `gamedir/`, or want it
named something else (maybe you already use the name 'gamedir' for your development ...),
you can do so by setting the `EVGAMEDIR` environment variable to the absolute path
of your alternative game dir. For example:

    ```
    EVGAMEDIR=/my/path/to/mygamedir make local
    ```

## Building for release

The full Evennia documentation also tracks documentation from older Evennia
versions. This is done by pulling documentation from Evennia's old release
branches and building them all so readers can choose which one to view. Only
specific official Evennia branches will be built, so you can't use this to
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

# Help with editing syntax

> This needs expanding in the future.

## Referring to a heading in the same file

You can self-reference by pointing to a header/label elsewhere in the
same document by using `#` and replacing any spaces in the name with `-`.

```
This is a [link to the heading](#My-Heading-Name).

# My Heading Name

```

## Referring to titles in another file

> WIP: Most of these special structures need more work and checking.

If file1 looks like this:

```
# Header title

```

You can refer to it from another file as

```
Read more about it [here](path.to.file1.md:Header title)


```
> This is not actually working at this time (WIP)

To refer to code in the Evennia repository, you can use a relative reference from the docs/ folder:

```
You can find this code [here](../evennia/objects/objects.py).

```
This will be automatically translated to the matching github link so the reader can click and jump to that code directly.
> This is not currently working. (WIP)


## Making toc-tree indices

To make a Table-of-Contents listing (what Sphinx refers to as a "Toc Tree"), one
must make new heading named either `Contents` or `Index`, followed by a bullet-list of
links:

```
# Index

- [Title1](doc1)
- [Title2](doc2)

```

This will create a toc-tree structure behind the scenes.



We may expand on this later. For now, check out existing docs and refer to the
[Markdown][commonmark] (CommonMark) specification.

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
[sphinx-autodoc]: http://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#module-sphinx.ext.autodoc
[sphinx-napoleon]: http://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
[getting-started]: https://github.com/evennia/evennia/wiki/Getting-Started
[contributing]: https://github.com/evennia/evennia/wiki/Contributing

