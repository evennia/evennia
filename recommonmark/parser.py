"""Docutils CommonMark parser"""

import sys
from os.path import splitext

from docutils import parsers, nodes
from sphinx import addnodes

from commonmark import Parser

from warnings import warn

if sys.version_info < (3, 0):
    from urlparse import urlparse
else:
    from urllib.parse import urlparse

__all__ = ['CommonMarkParser']


class CommonMarkParser(parsers.Parser):

    """Docutils parser for CommonMark"""

    supported = ('md', 'markdown')
    translate_section_name = None

    def __init__(self):
        self._level_to_elem = {}

    def parse(self, inputstring, document):
        self.document = document
        self.current_node = document
        self.setup_parse(inputstring, document)
        self.setup_sections()
        parser = Parser()
        ast = parser.parse(inputstring + '\n')
        self.convert_ast(ast)
        self.finish_parse()

    def convert_ast(self, ast):
        for (node, entering) in ast.walker():
            fn_prefix = "visit" if entering else "depart"
            fn_name = "{0}_{1}".format(fn_prefix, node.t.lower())
            fn_default = "default_{0}".format(fn_prefix)
            fn = getattr(self, fn_name, None)
            if fn is None:
                fn = getattr(self, fn_default)
            fn(node)

    # Node type enter/exit handlers
    def default_visit(self, mdnode):
        pass

    def default_depart(self, mdnode):
        """Default node depart handler

        If there is a matching ``visit_<type>`` method for a container node,
        then we should make sure to back up to it's parent element when the node
        is exited.
        """
        if mdnode.is_container():
            fn_name = 'visit_{0}'.format(mdnode.t)
            if not hasattr(self, fn_name):
                warn("Container node skipped: type={0}".format(mdnode.t))
            else:
                self.current_node = self.current_node.parent

    def visit_heading(self, mdnode):
        # Test if we're replacing a section level first
        if isinstance(self.current_node, nodes.section):
            if self.is_section_level(mdnode.level, self.current_node):
                self.current_node = self.current_node.parent

        title_node = nodes.title()
        title_node.line = mdnode.sourcepos[0][0]

        new_section = nodes.section()
        new_section.line = mdnode.sourcepos[0][0]
        new_section.append(title_node)

        self.add_section(new_section, mdnode.level)

        # Set the current node to the title node to accumulate text children/etc
        # for heading.
        self.current_node = title_node

    def depart_heading(self, _):
        """Finish establishing section

        Wrap up title node, but stick in the section node. Add the section names
        based on all the text nodes added to the title.
        """
        assert isinstance(self.current_node, nodes.title)
        # The title node has a tree of text nodes, use the whole thing to
        # determine the section id and names
        text = self.current_node.astext()
        if self.translate_section_name:
            text = self.translate_section_name(text)
        name = nodes.fully_normalize_name(text)
        section = self.current_node.parent
        section['names'].append(name)
        self.document.note_implicit_target(section, section)
        self.current_node = section

    def visit_text(self, mdnode):
        self.current_node.append(nodes.Text(mdnode.literal, mdnode.literal))

    def visit_softbreak(self, _):
        self.current_node.append(nodes.Text('\n'))

    def visit_paragraph(self, mdnode):
        p = nodes.paragraph(mdnode.literal)
        p.line = mdnode.sourcepos[0][0]
        self.current_node.append(p)
        self.current_node = p

    def visit_emph(self, _):
        n = nodes.emphasis()
        self.current_node.append(n)
        self.current_node = n

    def visit_strong(self, _):
        n = nodes.strong()
        self.current_node.append(n)
        self.current_node = n

    def visit_code(self, mdnode):
        n = nodes.literal(mdnode.literal, mdnode.literal)
        self.current_node.append(n)

    def visit_link(self, mdnode):
        ref_node = nodes.reference()
        # Check destination is supported for cross-linking and remove extension
        destination = mdnode.destination
        _, ext = splitext(destination)
        # TODO check for other supported extensions, such as those specified in
        # the Sphinx conf.py file but how to access this information?
        # TODO this should probably only remove the extension for local paths,
        # i.e. not uri's starting with http or other external prefix.
        if ext.replace('.', '') in self.supported:
            destination = destination.replace(ext, '')
        ref_node['refuri'] = destination
        # TODO okay, so this is acutally not always the right line number, but
        # these mdnodes won't have sourcepos on them for whatever reason. This
        # is better than 0 though.
        ref_node.line = self._get_line(mdnode)
        if mdnode.title:
            ref_node['title'] = mdnode.title
        next_node = ref_node

        url_check = urlparse(destination)
        if not url_check.scheme and not url_check.fragment:
            wrap_node = addnodes.pending_xref(
                reftarget=destination,
                reftype='any',
                refdomain=None,  # Added to enable cross-linking
                refexplicit=True,
                refwarn=True
            )
            # TODO also not correct sourcepos
            wrap_node.line = self._get_line(mdnode)
            if mdnode.title:
                wrap_node['title'] = mdnode.title
            wrap_node.append(ref_node)
            next_node = wrap_node

        self.current_node.append(next_node)
        self.current_node = ref_node

    def depart_link(self, mdnode):
        if isinstance(self.current_node.parent, addnodes.pending_xref):
            self.current_node = self.current_node.parent.parent
        else:
            self.current_node = self.current_node.parent

    def visit_image(self, mdnode):
        img_node = nodes.image()
        img_node['uri'] = mdnode.destination

        if mdnode.title:
            img_node['alt'] = mdnode.title

        self.current_node.append(img_node)
        self.current_node = img_node

    def visit_list(self, mdnode):
        list_node = None
        if (mdnode.list_data['type'] == "bullet"):
            list_node_cls = nodes.bullet_list
        else:
            list_node_cls = nodes.enumerated_list
        list_node = list_node_cls()
        list_node.line = mdnode.sourcepos[0][0]

        self.current_node.append(list_node)
        self.current_node = list_node

    def visit_item(self, mdnode):
        node = nodes.list_item()
        node.line = mdnode.sourcepos[0][0]
        self.current_node.append(node)
        self.current_node = node

    def visit_code_block(self, mdnode):
        kwargs = {}
        if mdnode.is_fenced and mdnode.info:
            kwargs['language'] = mdnode.info
        text = ''.join(mdnode.literal)
        if text.endswith('\n'):
            text = text[:-1]
        node = nodes.literal_block(text, text, **kwargs)
        self.current_node.append(node)

    def visit_block_quote(self, mdnode):
        q = nodes.block_quote()
        q.line = mdnode.sourcepos[0][0]
        self.current_node.append(q)
        self.current_node = q

    def visit_html(self, mdnode):
        raw_node = nodes.raw(mdnode.literal,
                             mdnode.literal, format='html')
        if mdnode.sourcepos is not None:
            raw_node.line = mdnode.sourcepos[0][0]
        self.current_node.append(raw_node)

    def visit_html_inline(self, mdnode):
        self.visit_html(mdnode)

    def visit_html_block(self, mdnode):
        self.visit_html(mdnode)

    def visit_thematic_break(self, _):
        self.current_node.append(nodes.transition())

    # Section handling
    def setup_sections(self):
        self._level_to_elem = {0: self.document}

    def add_section(self, section, level):
        parent_level = max(
            section_level for section_level in self._level_to_elem
            if level > section_level
        )
        parent = self._level_to_elem[parent_level]
        parent.append(section)
        self._level_to_elem[level] = section

        # Prune level to limit
        self._level_to_elem = dict(
            (section_level, section)
            for section_level, section in self._level_to_elem.items()
            if section_level <= level
        )

    def is_section_level(self, level, section):
        return self._level_to_elem.get(level, None) == section

    def _get_line(self, mdnode):
        while mdnode:
            if mdnode.sourcepos:
                return mdnode.sourcepos[0][0]
            mdnode = mdnode.parent
        return 0
