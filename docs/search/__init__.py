"""
Custom Evennia search plugin. This combines code from sphinxplugin-lunr and the
Mkdocs search implementation.

"""
from os.path import dirname, join, exists
from os import makedirs
import json
import sphinx.search
from six import iteritems
from sphinx.util.osutil import copyfile
from sphinx.jinja2glue import SphinxFileSystemLoader


# Sphinx setup

lunr = None
try:
    import lunr
except ImportError:
    pass


def _make_iter(inp):
    """make sure input is an iterable"""
    if not hasattr(inp, "__iter__"):
        return (inp, )
    return inp


class IndexBuilder(sphinx.search.IndexBuilder):
    def freeze(self):
        """Create a usable data structure for serializing."""
        data = super(IndexBuilder, self).freeze()
        try:
            # Sphinx >= 1.5 format
            # Due to changes from github.com/sphinx-doc/sphinx/pull/2454
            base_file_names = data['docnames']
        except KeyError:
            # Sphinx < 1.5 format
            base_file_names = data['filenames']

        lunrdocuments = []
        for prefix, items in iteritems(data['objects']):
            # This parses API objects
            for name, (index, typeindex, _, shortanchor) in iteritems(items):
                objtype = data['objtypes'][typeindex]

                if objtype.startswith("py:"):
                    # Python API entitites
                    last_prefix = prefix.split('.')[-1]
                    if objtype == "py:method":
                        displayname = last_prefix + "." + name
                    else:
                        displayname = prefix + "." + name

                else:
                    last_prefix = prefix.split('.')[-1]
                    displayname = name

                anchor = f"#{shortanchor}" if shortanchor else ''
                lunrdocuments.append({
                    'location': base_file_names[index] + anchor,
                    'title': displayname,
                    'text': prefix
                })

        titles = data['titles']
        for titleterm, indices in data['titleterms'].items():
            # Title components; the indices map to index in base_file_name
            for index in _make_iter(indices):
                lunrdocuments.append({
                    'location': base_file_names[index],
                    'title': titles[index],
                    'text': titleterm
                })

        # this is just too big for regular use
        # for term, indices in data['terms'].items():
        #     # In-file terms
        #     for index in _make_iter(indices):
        #         ref = next(c)
        #         lunrdocuments[ref] = {
        #             'ref': str(ref),
        #             'filename': base_file_names[index],
        #             'objtype': "",
        #             'prefix': term,
        #             'last_prefix': '',
        #             'name': titles[index],
        #             'displayname': titles[index],
        #             'shortanchor': ''
        #         }

        if not lunr:
            print("\npython package `lunr==0.5.8` required in order "
                  "to pre-build search index.")
            return data

        print("\nPre-building search index using python-lunr ...")
        # pre-compile the data store into a lunr index
        fields = ["location", "title", "text"]
        lunr_index = lunr.lunr(ref='location', fields=fields,
                               documents=lunrdocuments)
        lunr_index = lunr_index.serialize()

        # required by js file
        page_store = {
            "config": {"lang": ['en'],
                       "separator": r'\s\-]+',
                       "min_search_length": 3,
                       "prebuild_index": "python"},
            "docs": lunrdocuments,
            "index": lunr_index
        }

        lunr_index_json = json.dumps(page_store, sort_keys=True,
                                     separators=(',', ':'))
        try:
            fname = join(dirname(__file__), "js", "search", "search_index.json")
            with open(fname, 'w') as fil:
                fil.write(lunr_index_json)
        except Exception as err:
            print("Failed saving lunr index to", fname, err)

        return data


def builder_inited(app):
    """
    Adding a new loader to the template system puts our searchbox.html
    template in front of the others, it overrides whatever searchbox.html
    the current theme is using.
    it's still up to the theme to actually _use_ a file called searchbox.html
    somewhere in its layout. but the base theme and pretty much everything
    else that inherits from it uses this filename.
    """
    app.builder.templates.loaders.insert(0, SphinxFileSystemLoader(dirname(__file__)))


def copy_static_files(app, _):
    """
    Because we're using the extension system instead of the theme system, it's
    our responsibility to copy over static files outselves.  files =
    [join('js', 'searchbox.js'), join('css', 'searchbox.css')]
    """
    files = [join('js', 'search', 'main.js'),
             join('js', 'search', 'worker.js'),
             join('js', 'search', 'lunr.js')]

    if lunr:
        files.append(join('js', 'search', "search_index.json"))

    for f in files:
        src = join(dirname(__file__), f)
        dest = join(app.outdir, '_static', f)
        if not exists(dirname(dest)):
            makedirs(dirname(dest))
        copyfile(src, dest)


def setup(app):
    # adds <script> and <link> to each of the generated pages to load these
    # files.
    app.add_stylesheet('css/searchbox.css')
    app.add_javascript('js/search/main.js')

    app.connect('builder-inited', builder_inited)
    app.connect('build-finished', copy_static_files)

    app.add_config_value("search_index_pregenerate", True, 'html')
    app.add_config_value("search_index_python", False, 'html')

    sphinx.search.IndexBuilder = IndexBuilder
