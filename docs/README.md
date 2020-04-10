# evennia-docs
Documentation for the Evennia MUD creation system.

This system is still WIP! 

The live documentation (will in the future be) is available at `https://evennia.github.io/evennia/`.

# Editing the docs

The docs source files are `*.md` files found in `evennia/docs/source/`.  They
are simple text files that can be edited with a normal text editor and needs to
be decorated with [Markdown][commonmark] syntax. 

Don't edit the files in `source/api/`. These are auto-generated and your changes 
will be lost. 


# Building the docs

The sources in `evennia/docs/source/` are built into a pretty documentation using
the [Sphinx][sphinx] static generator system. 

You don't necessarily _have_ to build the docs locally to commit changes to the
docs; they are just text files after all. But building them allows you to check
for yourself that syntax is correct and that your change comes out looking as
you expect before contributing.

## Prerequisites

### Only the main documentation

If you only want to build the main documentation pages (not the API autodocs),
you don't need to install Evennia itself, only the documentation resources.
All is done in your terminal/console. 

- (Optional, but recommended): Activate a virtualenv with Python3.7.
- `cd` to into the `evennia/docs` folder (where this README is)
- Run `make install` or `pip install -r requirements.txt` to install the documentation-build
  requirements.
- `make quick` - this will create html-based documentation in the new 
  folder `evennia/docs/builds/html/`. 
- Use a web browser to open `evennia/docs/builds/html/index.html` and read the rendered docs.

### Main documentation and API docs

The full documentation includes both the doc pages and the API documentation
generated from the Evennia source. For this you must install Evennia and
initialize a new game with a default database (you don't need to have it
running)

- Follow the normal [Evennia Getting-Started instructions][getting-started] 
  to install Evennia. Use a virtualenv.
- Make sure you `cd` to the folder containing your `evennia/` repo. 
- Create a new game folder called `gamedir` next to your regular game dir (if you
  have the same level as your `evennia`
repo with `evennia --init gamedir`. Then `cd` into it and run `evennia migrate`
to create the database. You don't need to continue to start the game.
- This is how the structure should look at this point:

```
  (top)
  |
  ----- evennia/  (the top-level folder, where docs/ is)
  |
  ----- gamedir/
```

- Go to `evennia/docs/` and run `make install` or `pip install -r requirements.txt` 
  to install the doc-building requirements into your virtualenv. 

## Building locally

With your build environment set up as above, stand in the `evennia/docs` directory and run

    make local

This will build the html documentation (including api docs) in the new folder
`evennia/docs/build/html/`. To read it, open `evennia/docs/build/html/index.html` in any web browser.

Building the api docs can be quite slow. If you are working on some doc change
and just want to quickly check that things came out the way you want, you can
also opt to only build the normal docs:

    make quick

You will get errors from the api index and won't be able to view the api-docs, but it's
a lot faster to run! This will not clean out the `build/` dir between runs. If you
find you get any old stuff hanging around in the
`build/` dir you can use

    make clear

to remove any old build cruft before next quick-build.


## Building for release

The release-build will build all documentation branches. Only official Evennia
branches will be built so you can't use this to build your own testing branch.

- All local changes must have been committed to git first, since the docs build
by looking at the git tree.
- To build for local checking, run

    make mv-local

- Once all is built and it looks ok, run

    make deploy

Note that this step requires git-push access to the Evennia `gh-pages` branch on `github`.

If you know what you are doing you can also do

    make release

This does the build + deploy steps automatically.


# Contributing and editing documentation

Check out the branch of Evennia you want to edit the documentation for. Then make your own
branch off this, make your changes and make a PR for it!

The documentation sources are in `evennia/docs/source/`. These are mainly
[Markdown][commonmark] (`.md`) files that you can edit like normal text files.
The ReST files in `source/api/` are auto-generated from the Evennia sources and
should _not_ be manually edited.


# Help with editing syntax

## Referring to titles in another file


If file1 looks like this:

```
# Header title

```
You can refer to it from another file as

```
Read more about it [here](path.to.file1.md:Header title)


```

To refer to code in the Evennia repository, you can use a relative reference from the docs/ folder:

```
You can find this code [here](../evennia/objects/objects.py).

```

This will be automatically translated to the matching github link so the reader can click and jump to that code directly.


## Making indices

To make a document tree (what Sphinx refers to as a "Toc Tree"), make a list of document urls like this:

```
* [Title1](doc1.md)
* [Title2](doc2.md)

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

