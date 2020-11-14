# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import re
from recommonmark.transform import AutoStructify
from sphinx.util.osutil import cd


# -- Project information -----------------------------------------------------

project = "Evennia"
copyright = "2020, The Evennia developer community"
author = "The Evennia developer community"

# The full Evennia version covered by these docs, including alpha/beta/rc tags
# This will be used for multi-version selection options.
release = "0.9.5"


# -- General configuration ---------------------------------------------------

extensions = [
    "recommonmark",
    "sphinx_multiversion",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.viewcode",
    # "sphinxcontrib.lunrsearch",
    "sphinx.ext.todo",
    "sphinx.ext.githubpages",
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
        "versioning.html",
    ]
}
html_favicon = "_static/images/favicon.ico"
html_logo = "_static/images/evennia_logo.png"
html_short_title = "Evennia"

# HTML syntax highlighting style
pygments_style = "sphinx"


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


# -- Recommonmark ------------------------------------------------------------
# allows for writing Markdown and convert to rst dynamically

# reroute to github links or to the api

_github_code_root = "https://github.com/evennia/evennia/blob/"
_github_doc_root = "https://github.com/evennia/tree/master/docs/sources/"
_github_issue_choose = "https://github.com/evennia/evennia/issues/new/choose"


def url_resolver(url):
    """
    Convert urls by catching special markers.
    """
    githubstart = "github:"
    apistart = "api:"
    choose_issue = "github:issue"
    sourcestart = "src:"

    if url.endswith(choose_issue):
        return _github_issue_choose
    elif githubstart in url:
        urlpath = url[url.index(githubstart) + len(githubstart) :]
        if not (urlpath.startswith("develop/") or urlpath.startswith("master")):
            urlpath = "master/" + urlpath
        return _github_code_root + urlpath
    elif apistart in url:
        # locate the api/ folder in the doc structure
        ind = url.index(apistart)
        depth = url[:ind].count("/") + 1
        path = "../".join("" for _ in range(depth))
        urlpath = path + "api/" + url[ind + len(apistart) :] + ".html"
        return urlpath
    elif sourcestart in url:
        ind = url.index(sourcestart)
        depth = url[:ind].count("/") + 1
        path = "../".join("" for _ in range(depth))

        modpath, *inmodule = url[ind + len(sourcestart) :].rsplit("#", 1)
        modpath = "/".join(modpath.split("."))
        inmodule = "#" + inmodule[0] if inmodule else ""
        modpath = modpath + ".html" + inmodule

        urlpath = path + "_modules/" + modpath
        return urlpath

    return url


# auto-create TOCs if a list of links is under these headers
auto_toc_sections = ["Contents", "Toc", "Index", "API", "Overview"]

recommonmark_config = {
    "enable_auto_toc_tree": True,
    "url_resolver": url_resolver,
    "auto_toc_maxdepth": 1,
    "auto_toc_tree_section": ["Contents", "Toc", "Index"],
    "code_highlight_options": {"force": True, "linenos": True},
}


# -- API/Autodoc ---------------------------------------------------------------
# automatic creation of API documentation. This requires a valid Evennia setup

_no_autodoc = os.environ.get("NOAUTODOC")

ansi_clean = None

if not _no_autodoc:
    # we must set up Evennia and its paths for autodocs to work

    EV_ROOT = os.environ.get("EVDIR")
    GAME_DIR = os.environ.get("EVGAMEDIR")

    if not (EV_ROOT and GAME_DIR):
        err = (
            "The EVDIR and EVGAMEDIR environment variables must be set to "
            "the absolute paths to the evennia/ repo and an initialized "
            "evennia gamedir respectively."
        )
        raise RuntimeError(err)

    print("Evennia root: {}, Game dir: {}".format(EV_ROOT, GAME_DIR))

    sys.path.insert(1, EV_ROOT)
    sys.path.insert(1, GAME_DIR)

    with cd(GAME_DIR):
        # set up Evennia so its sources can be parsed
        os.environ["DJANGO_SETTINGS_MODULE"] = "server.conf.settings"

        import django  # noqa

        django.setup()

        import evennia  # noqa

        evennia._init()

    from evennia.utils.ansi import strip_raw_ansi as ansi_clean


if _no_autodoc:
    exclude_patterns = ["api/*"]
else:
    exclude_patterns = ["api/*migrations.rst"]

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    "special-members": "__init__",
    "enable_eval_rst": True,
    # "inherited_members": True
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
    app.add_transform(AutoStructify)

    # build toctree file
    sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from docs.pylib import auto_link_remapper

    _no_autodoc = os.environ.get("NOAUTODOC")
    auto_link_remapper.auto_link_remapper(no_autodoc=_no_autodoc)
    print("Updated source/toc.md file")

    # custom lunr-based search
    # from docs import search
    # custom search
    # search.setup(app)
