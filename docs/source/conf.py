# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys
from os.path import sep, abspath, dirname, join as pathjoin, exists
import recommonmark
from recommonmark.transform import AutoStructify
from sphinx.util.osutil import cd

# we must set up Evennia and its paths for autodocs to work

EV_ROOT = os.environ.get("EVDIR")
GAME_DIR = os.environ.get("EVGAMEDIR")

if not (EV_ROOT and GAME_DIR):
    print("The EVDIR and EVGAMEDIR environment variables must be set to the "
          "absolute paths to the evennia/ repo and an initialized evennia "
          "gamedir respectively.")
    raise RuntimeError()

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
release = '0.9'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "recommonmark",
    "sphinx.ext.napoleon",
    "sphinx_multiversion"
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Custom extras for sidebar
html_sidebars = {
    '**': [
        "versioning.html"
    ]
}

# sphinx-multiversion config

smv_tag_whitelist = r""
smv_branch_whitelist = r"^static-file-docs$"
smv_outputdir_format = "versions" + sep + "{config.release}"

# dynamic setup


github_doc_root = "https://github.com/evennia/tree/master/docs/"


def setup(app):
    # recommonmark setup
    app.add_config_value('recommonmark_config', {
            'url_resolver': lambda url: github_doc_root + url,
            'auto_toc_tree_section': 'Contents',
            }, True)
    app.add_transform(AutoStructify)
