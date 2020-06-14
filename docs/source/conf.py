# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
import sphinx_theme
from recommonmark.transform import AutoStructify
from sphinx.util.osutil import cd


# -- Project information -----------------------------------------------------

project = "Evennia"
copyright = "2020, The Evennia developer community"
author = "The Evennia developer community"

# The full Evennia version covered by these docs, including alpha/beta/rc tags
# This will be used for multi-version selection options.
release = "0.9.1"


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

source_suffix = ['.md', '.rst']
master_doc = 'index'

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
smv_branch_whitelist = r"^master$|^develop$|^v[0-9\.]+?$"
smv_outputdir_format = "{config.release}"
# don't make docs for tags
smv_tag_whitelist = r"^$"


# -- Options for HTML output -------------------------------------------------

# html_theme = "alabaster"
html_theme = "stanford_theme"
html_theme_path = [sphinx_theme.get_html_theme_path("stanford_theme")]

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
html_favicon = "_static/favicon.ico"

# HTML syntax highlighting style
pygments_style = "sphinx"


# -- Options for LaTeX output ------------------------------------------------
# experimental, not working well atm

latex_engine = 'xelatex'
latex_show_urls = 'footnote'
latex_elements = {
    'papersize': 'a4paper',
    'fncychap': r'\usepackage[Bjarne]{fncychap}',
    'fontpkg': r'\usepackage{times,amsmath,amsfonts,amssymb,amsthm}',
    'preamble': r'''
        \usepackage[utf8]{fontenc}
        \usepackage{amsmath,amsfonts,amssymb,amsthm}
        \usepackage[math-style=literal]{unicode-math}
        \usepackage{newunicodechar}
        \usepackage{graphicx}
    '''
}
latex_documents = [
    (master_doc,  'main.tex', 'Sphinx format', 'Evennia', 'report'),
    ("toc", 'toc.tex', 'TOC', 'Evennia', 'report')
]


# -- Recommonmark ------------------------------------------------------------
# allows for writing Markdown and convert to rst dynamically

# reroute to github links or to the api

_github_code_root = "https://github.com/evennia/evennia/blob/"
_github_doc_root = "https://github.com/evennia/tree/master/docs/sources/"
_github_issue_choose = "https://github.com/evennia/evennia/issues/new/choose"


def url_resolver(url):
    githubstart = "github:"
    apistart = "api:"
    choose_issue = ("feature-request", "report-bug", "issue", "bug-report")

    if url.lower().strip() in choose_issue:
        return _github_issue_choose

    elif url.startswith(githubstart):
        urlpath = url[len(githubstart):]
        if not (urlpath.startswith("develop/") or urlpath.startswith("master")):
            urlpath = "master/" + urlpath 
        return _github_code_root + urlpath
    elif url.startswith(apistart):
        return "api/" + url[len(apistart) :] + ".html"
    return url
    # else:
    #     return _github_doc_root + url


# auto-create TOCs if a list of links is under these headers
auto_toc_sections = ["Contents", "Toc", "Index"]

recommonmark_config = {
    "enable_auto_toc_tree": True,
    "url_resolver": url_resolver,
    "auto_toc_tree_section": ["Contents", "Toc", "Index"],
    "code_highlight_options": {"force": True, "linenos": True},
}


# -- API/Autodoc ---------------------------------------------------------------
# automatic creation of API documentation. This requires a valid Evennia setup

_no_autodoc = os.environ.get("NOAUTODOC")

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

if _no_autodoc:
    exclude_patterns = ["api/*"]
else:
    exclude_patterns = ["api/*migrations.rst"]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "special-members": "__init__",
    "enable_eval_rst": True,
}


def autodoc_skip_member(app, what, name, obj, skip, options):
    if _no_autodoc:
        return True
    if name.startswith("__") and name != "__init__":
        return True
    return False


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
napoleon_use_rtype = True


# -- Main config setup ------------------------------------------
# last setup steps for some plugins


def setup(app):
    app.connect("autodoc-skip-member", autodoc_skip_member)
    app.add_transform(AutoStructify)

    # custom lunr-based search
    # from docs import search
    # custom search
    # search.setup(app)
