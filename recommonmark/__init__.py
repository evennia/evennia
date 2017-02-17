"""Docutils CommonMark parser"""

__version__ = '0.4.0'


def setup(app):
    """Initialize Sphinx extension."""
    from .parser import CommonMarkParser
    app.add_source_parser('.md', CommonMarkParser)  # needs Sphinx >= 1.4
    return {'version': __version__, 'parallel_read_safe': True}
