# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from os.path import sep
from recommonmark.transform import AutoStructify
from sphinx.util.osutil import cd


_no_autodoc = os.environ.get("NOAUTODOC")

if not _no_autodoc:
    # we must set up Evennia and its paths for autodocs to work

    EV_ROOT = os.environ.get("EVDIR")
    GAME_DIR = os.environ.get("EVGAMEDIR")

    if not (EV_ROOT and GAME_DIR):
<<<<<<< HEAD
        err = ("The EVDIR and EVGAMEDIR environment variables must be set to "
              "the absolute paths to the evennia/ repo and an initialized "
              "evennia gamedir respectively.")
        raise RuntimeError(err)
=======
        print("The EVDIR and EVGAMEDIR environment variables must be set to "
              "the absolute paths to the evennia/ repo and an initialized "
              "evennia gamedir respectively.")
        raise RuntimeError()
>>>>>>> master

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


# -- Project information -----------------------------------------------------

project = 'Evennia'
copyright = '2020, The Evennia developer community'
author = 'The Evennia developer community'

# The full version, including alpha/beta/rc tags
<<<<<<< HEAD
release = '1.0-dev'
=======
release = '0.9.1'
>>>>>>> master

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "recommonmark",
    "sphinx_multiversion",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.viewcode",
    # "sphinxcontrib.lunrsearch",
]

# make sure sectionlabel references can be used as path/to/file:heading
autosectionlabel_prefix_document = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Custom extras for sidebar
html_sidebars = {
    '**': [
        "searchbox.html",
        "localtoc.html",
        # "globaltoc.html",
        "relations.html",
        "sourcelink.html",
        "versioning.html",
    ]
}


# napoleon Google-style docstring parser

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


# settings for sphinxcontrib.apidoc to auto-run sphinx-apidocs

if _no_autodoc:
    exclude_patterns = ["api/*"]
else:
    exclude_patterns = ["api/*migrations.rst"]

# for inline autodoc

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



# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'


# sphinx-multiversion config

smv_tag_whitelist = r"^$"
<<<<<<< HEAD
smv_branch_whitelist = r"^master$|^develop$"
# which branches to include in multi-version docs
# - master, develop and vX.X branches 
smv_branch_whitelist = r"^master$|^develop$|^v[0-9\.]+?$"
=======
# smv_branch_whitelist = r"^static-file-docs$|^static-file-dev$"
smv_branch_whitelist = r"^master$|^v1.0$"
>>>>>>> master
smv_outputdir_format = "versions" + sep + "{config.release}"


# recommonmark

# reroute to github links or to the api

_github_code_root = "https://github.com/evennia/evennia/blob/master/"
_github_doc_root = "https://github.com/evennia/tree/master/docs/sources/"
_github_issue_choose = "https://github.com/evennia/evennia/issues/new/choose"


def url_resolver(url):
    urlstart = "github:"
    apistart = "api:"
    choose_issue = ("feature-request", "report-bug", "issue")

    if url.lower().strip() in choose_issue:
        return _github_issue_choose
    elif url.startswith(urlstart):
        return _github_code_root + url[len(urlstart):]
    elif url.startswith(apistart):
        print("api: -> api ref")
        return "api/" + url[len(apistart):] + ".html"
    return url
    # else:
    #     return _github_doc_root + url


# auto-create TOCs if a list of links is under these headers
auto_toc_sections = ["Contents", "Toc", "Index"]

recommonmark_config = {
    "enable_auto_toc_tree": True,
    "url_resolver": url_resolver,
    "auto_toc_tree_section": ["Contents", "Toc", "Index"],
    "code_highlight_options": {"force": True,
                               "linenos": True}
}


def setup(app):
    app.connect("autodoc-skip-member", autodoc_skip_member)
    app.add_transform(AutoStructify)

    # custom lunr-based search
    # from docs import search
    # custom search
    # search.setup(app)
