# recommonmark

A `docutils`-compatibility bridge to [CommonMark][cm].

This allows you to write CommonMark inside of Docutils & Sphinx projects.

Documentation is available on Read the Docs: <http://recommonmark.readthedocs.org>

Contents
--------

* [API Reference](api_ref.md)
* [AutoStructify Component](auto_structify.md)

## Getting Started

To use `recommonmark` inside of Sphinx only takes 2 steps. 
First you install it:

```
pip install recommonmark 
```

Then add this to your Sphinx conf.py:

```
# for Sphinx-1.4 or newer
extensions = ['recommonmark']

# for Sphinx-1.3
from recommonmark.parser import CommonMarkParser

source_parsers = {
    '.md': CommonMarkParser,
}

source_suffix = ['.rst', '.md']
```

This allows you to write both `.md` and `.rst` files inside of the same project.

### Links

For all links in commonmark that aren't explicit URLs, they are treated as cross references with the [`:any:`](http://www.sphinx-doc.org/en/stable/markup/inline.html#role-any) role. This allows referencing a lot of things including files, labels, and even objects in the loaded domain.

### AutoStructify

AutoStructify makes it possible to write your documentation in Markdown, and automatically convert this
into rST at build time. See [the AutoStructify Documentation](http://recommonmark.readthedocs.org/en/latest/auto_structify.html)
for more information about configuration and usage.

To use the advanced markdown to rst transformations you must add `AutoStructify` to your Sphinx conf.py.

```python
# At top on conf.py (with other import statements)
import recommonmark
from recommonmark.transform import AutoStructify

# At the bottom of conf.py
def setup(app):
    app.add_config_value('recommonmark_config', {
            'url_resolver': lambda url: github_doc_root + url,
            'auto_toc_tree_section': 'Contents',
            }, True)
    app.add_transform(AutoStructify)
```

See https://github.com/rtfd/recommonmark/blob/master/docs/conf.py for a full example.

AutoStructify comes with the following options. See [http://recommonmark.readthedocs.org/en/latest/auto_structify.html](http://recommonmark.readthedocs.org/en/latest/auto_structify.html) for more information about the specific features.

* __enable_auto_toc_tree__: enable the Auto Toc Tree feature.
* __auto_toc_tree_section__: when True, Auto Toc Tree will only be enabled on section that matches the title.
* __enable_auto_doc_ref__: enable the Auto Doc Ref feature. **Deprecated**
* __enable_math__: enable the Math Formula feature.
* __enable_inline_math__: enable the Inline Math feature.
* __enable_eval_rst__: enable the evaluate embedded reStructuredText feature.
* __url_resolver__: a function that maps a existing relative position in the document to a http link

## Development

You can run the tests by running `tox` in the top-level of the project.

We are working to expand test coverage,
but this will at least test basic Python 2 and 3 compatability.

## Why a bridge?

Many python tools (mostly for documentation creation) rely on `docutils`.
But [docutils][dc] only supports a ReStructuredText syntax.

For instance [this issue][sphinx-issue] and [this StackOverflow
question][so-question] show that there is an interest in allowing `docutils`
to use markdown as an alternative syntax.

## Why another bridge to docutils?

recommonmark uses the [python implementation][pcm] of [CommonMark][cm] while
[remarkdown][rmd] implements a stand-alone parser leveraging [parsley][prs].

Both output a [`docutils` document tree][dc] and provide scripts
that leverage `docutils` for generation of different types of documents.

## Acknowledgement

recommonmark is mainly derived from [remarkdown][rmd] by Steve Genoud and
leverages the python CommonMark implementation.

It was originally created by [Luca Barbato][lu-zero],
and is now maintained in the Read the Docs (rtfd) GitHub organization.

[cm]: http://commonmark.org
[pcm]: https://github.com/rtfd/CommonMark-py
[rmd]: https://github.com/sgenoud/remarkdown
[prs]: https://github.com/python-parsley/parsley
[lu-zero]: https://github.com/lu-zero

[dc]: http://docutils.sourceforge.net/docs/ref/doctree.html
[sphinx-issue]: https://bitbucket.org/birkenfeld/sphinx/issue/825/markdown-capable-sphinx
[so-question]: http://stackoverflow.com/questions/2471804/using-sphinx-with-markdown-instead-of-rst
