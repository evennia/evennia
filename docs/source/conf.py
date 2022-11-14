# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import re
import sys

# from recommonmark.transform import AutoStructify
from sphinx.util.osutil import cd

# -- Project information -----------------------------------------------------

project = "Evennia"
copyright = "2022, The Evennia developer community"
author = "The Evennia developer community"

# The full Evennia version covered by these docs, including alpha/beta/rc tags
# This will be used for multi-version selection options.
release = "1.0-dev"


# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx_multiversion",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx.ext.githubpages",
    "myst_parser",
]

source_suffix = [".md", ".rst"]
master_doc = "index"

# make sure sectionlabel references can be used as path/to/file:heading
autosectionlabel_prefix_document = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


# -- Sphinx-multiversion config ----------------------------------------------

# which branches to include in multi-versioned docs
# - master, develop and vX.X branches
smv_branch_whitelist = r"^develop$|^v[0-9\.]+?$"
smv_outputdir_format = "{config.release}"
# don't make docs for tags
smv_tag_whitelist = r"^$"
# legacy branches are linked to in template, but not built (custom for Evennia)
smv_legacy_branches = ["0.9.5"]


# -- Options for HTML output -------------------------------------------------

html_theme = "nature"

# Custom extras for sidebar
html_sidebars = {
    "**": [
        "searchbox.html",
        "localtoc.html",
        # "globaltoc.html",
        "relations.html",
        "sourcelink.html",
        "links.html",
        "versioning.html",
    ]
}
html_favicon = "_static/images/favicon.ico"
html_logo = "_static/images/evennia_logo.png"
html_short_title = "Evennia"

# HTML syntax highlighting style
pygments_style = "friendly"


# -- Options for LaTeX output ------------------------------------------------
# experimental, not working well atm

latex_engine = "xelatex"
latex_show_urls = "footnote"
latex_elements = {
    "papersize": "a4paper",
    "fncychap": r"\usepackage[Bjarne]{fncychap}",
    "fontpkg": r"\usepackage{times,amsmath,amsfonts,amssymb,amsthm}",
    "preamble": r"""
        \usepackage[utf8]{fontenc}
        \usepackage{amsmath,amsfonts,amssymb,amsthm}
        \usepackage[math-style=literal]{unicode-math}
        \usepackage{newunicodechar}
        \usepackage{graphicx}
    """,
}
latex_documents = [
    (master_doc, "main.tex", "Sphinx format", "Evennia", "report"),
    ("toc", "toc.tex", "TOC", "Evennia", "report"),
]


# -- MyST Markdown parsing -----------------------------------------------------

myst_enable_extensions = [
    "amsmath",
    "colon_fence",  # Use ::: instead of ``` for some extra features
    "deflist",  # use : to mark sublevel of list
    "dollarmath",
    "html_admonition",  # Add admonitions in html (usually use ```{admonition} directive)
    "html_image",  # parse raw <img ...> </img> tags
    "linkify",  # convert bare urls to md links
    "replacements",  # (c) to copyright sign etc
    "smartquotes",
    "substitution",
    "tasklist",
]

myst_dmath_allow_space = False  # requires $a$, not $ a$ or $a $
myst_dmath_allow_digits = False  # requires $a$, not 1$a$ or $a$2
myst_dmath_double_inline = True  # allow $$ ... $$ math blocks

myst_substitution = {
    # used with Jinja2. Can also be set in a substitutions: block in front-matter of page
}
# add anchors to h1, h2, ... level headings
myst_heading_anchors = 4

suppress_warnings = ["myst.ref"]

# reroute to github links or to the api

# shortcuts
_githubstart = "github:"
_apistart = "api:"
_choose_issue = "github:issue"
_sourcestart = "src:"
# remaps
_github_code_root = "https://github.com/evennia/evennia/blob/"
_github_doc_root = "https://github.com/evennia/tree/master/docs/sources/"
_github_issue_choose = "https://github.com/evennia/evennia/issues/new/choose"
_ref_regex = re.compile(  # normal reference-links [txt](url)
    r"\[(?P<txt>[\w -\[\]\`\n]+?)\]\((?P<url>.+?)\)", re.I + re.S + re.U + re.M
)
_ref_doc_regex = re.compile(  # in-document bottom references [txt]: url
    r"\[(?P<txt>[\w -\`]+?)\\n]:\s+?(?P<url>.+?)(?=$|\n)", re.I + re.S + re.U + re.M
)


def url_resolver(app, docname, source):
    """
    A handler acting on the `source-read` signal. The `source`
    is a list with one element that should be updated.
    Convert urls by catching special markers.

    Supported replacements (used e.g. as [txt](github:...)
        github:master/<url>  - add path to Evennia github master branch
        github:develop/<url> - add path to Evennia github develop branch
        github:issue - add link to the Evennia github issue-create page
        src:foo.bar#Foo - add link to source doc in _modules
        api:foo.bar#Foo - add link to api autodoc page


    """

    def _url_remap(url):

        # determine depth in tree of current document
        docdepth = docname.count("/") + 1
        relative_path = "../".join("" for _ in range(docdepth))

        if url.endswith(_choose_issue):
            # github:issue shortcut
            return _github_issue_choose
        elif _githubstart in url:
            # github:develop/... shortcut
            urlpath = url[url.index(_githubstart) + len(_githubstart) :]
            if not (urlpath.startswith("develop/") or urlpath.startswith("master")):
                urlpath = "master/" + urlpath
            return _github_code_root + urlpath
        elif _sourcestart in url:
            ind = url.index(_sourcestart)

            modpath, *inmodule = url[ind + len(_sourcestart) :].rsplit("#", 1)
            modpath = "/".join(modpath.split("."))
            inmodule = "#" + inmodule[0] if inmodule else ""
            modpath = modpath + ".html" + inmodule

            urlpath = relative_path + "_modules/" + modpath
            return urlpath

        return url

    def _re_ref_sub(match):
        txt = match.group("txt")
        url = _url_remap(match.group("url"))
        return f"[{txt}]({url})"

    def _re_docref_sub(match):
        txt = match.group("txt")
        url = _url_remap(match.group("url"))
        return f"[{txt}]: {url}"

    src = source[0]
    src = _ref_regex.sub(_re_ref_sub, src)
    src = _ref_doc_regex.sub(_re_docref_sub, src)
    source[0] = src


# # -- API/Autodoc ---------------------------------------------------------------
# # automatic creation of API documentation. This requires a valid Evennia setup

_no_autodoc = os.environ.get("NOAUTODOC")

ansi_clean = None

if not _no_autodoc:
    # we must set up Evennia and its paths for autodocs to work

    EV_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    sys.path.insert(1, EV_ROOT)

    with cd(EV_ROOT):
        # set up Evennia so its sources can be parsed
        os.environ["DJANGO_SETTINGS_MODULE"] = "evennia.settings_default"

        import django  # noqa

        django.setup()

        import evennia  # noqa

        evennia._init()

    from evennia.utils.ansi import strip_raw_ansi as ansi_clean

if _no_autodoc:
    exclude_patterns = ["api/*"]
else:
    exclude_patterns = ["api/*migrations.rst", "api/*migrations.md"]

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    "special-members": "__init__",
    "enable_eval_rst": True,
    "inherited_members": True,
}

autodoc_member_order = "bysource"
# autodoc_typehints = "description"


def autodoc_skip_member(app, what, name, obj, skip, options):
    """Which members the autodoc should ignore."""
    if _no_autodoc:
        return True
    if name.startswith("_") and name != "__init__":
        return True
    return False


def autodoc_post_process_docstring(app, what, name, obj, options, lines):
    """
    Post-process docstring in various ways. Must modify lines-list in-place.
    """
    try:

        # clean out ANSI colors

        if ansi_clean:
            for il, line in enumerate(lines):
                lines[il] = ansi_clean(line)

        # post-parse docstrings to convert any remaining
        # markdown -> reST since napoleon doesn't know Markdown

        def _sub_codeblock(match):
            code = match.group(1)
            return "::\n\n    {}".format("\n    ".join(lne for lne in code.split("\n")))

        underline_map = {
            1: "-",
            2: "=",
            3: "^",
            4: '"',
        }

        def _sub_header(match):
            # add underline to convert a markdown #header to ReST
            groupdict = match.groupdict()
            hashes, title = groupdict["hashes"], groupdict["title"]
            title = title.strip()
            lvl = min(max(1, len(hashes)), 4)
            return f"{title}\n" + (underline_map[lvl] * len(title))

        doc = "\n".join(lines)
        doc = re.sub(
            r"```python\s*\n+(.*?)```", _sub_codeblock, doc, flags=re.MULTILINE + re.DOTALL
        )
        doc = re.sub(r"```", "", doc, flags=re.MULTILINE)
        doc = re.sub(r"`{1}", "**", doc, flags=re.MULTILINE)
        doc = re.sub(
            r"^(?P<hashes>#{1,4})\s*?(?P<title>.*?)$", _sub_header, doc, flags=re.MULTILINE
        )

        newlines = doc.split("\n")
        # we must modify lines in-place
        lines[:] = newlines[:]

    except Exception as err:
        # if we don't print here we won't see what the error actually is
        print(f"Post-process docstring exception: {err}")
        raise


# Napoleon Google-style docstring parser for autodocs

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_keyword = True
napoleon_use_rtype = False


# -- Main config setup ------------------------------------------
# last setup steps for some plugins


def setup(app):
    app.connect("autodoc-skip-member", autodoc_skip_member)
    app.connect("autodoc-process-docstring", autodoc_post_process_docstring)
    app.connect("source-read", url_resolver)

    # build toctree file
    sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from docs.pylib import (
        auto_link_remapper,
        contrib_readmes2docs,
        update_default_cmd_index,
        update_dynamic_pages,
    )

    _no_autodoc = os.environ.get("NOAUTODOC")
    update_default_cmd_index.run_update(no_autodoc=_no_autodoc)
    contrib_readmes2docs.readmes2docs()
    update_dynamic_pages.update_dynamic_pages()
    auto_link_remapper.auto_link_remapper(no_autodoc=_no_autodoc)

    # custom lunr-based search
    # from docs import search
    # custom search
    # search.setup(app)
