"""Docutils CommonMark parser"""

__version__ = '0.5.0'


def setup(app):
    """Initialize Sphinx extension."""
    import sphinx
    from .parser import CommonMarkParser

    if sphinx.version_info >= (1, 8):
        app.add_source_suffix('.md', 'markdown')
        app.add_source_parser(CommonMarkParser)
    elif sphinx.version_info >= (1, 4):
        app.add_source_parser('.md', CommonMarkParser)

    return {'version': __version__, 'parallel_read_safe': True}
