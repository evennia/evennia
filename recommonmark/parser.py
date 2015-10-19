from contextlib import contextmanager
import itertools

from docutils import parsers, nodes

from CommonMark import DocParser, HTMLRenderer
from warnings import warn

__all__ = ['CommonMarkParser']


def flatten(iterator):
    return itertools.chain.from_iterable(iterator)


class _SectionHandler(object):

    def __init__(self, document):
        self._level_to_elem = {0: document}

    def _parent_elem(self, child_level):
        parent_level = max(level for level in self._level_to_elem
                           if child_level > level)
        return self._level_to_elem[parent_level]

    def _prune_levels(self, limit_level):
        self._level_to_elem = dict((level, elem)
                                   for level, elem in self._level_to_elem.items()
                                   if level <= limit_level)

    def add_new_section(self, section, level):
        parent = self._parent_elem(level)
        parent.append(section)
        self._level_to_elem[level] = section
        self._prune_levels(level)


class CommonMarkParser(parsers.Parser):

    """Parser of recommonmark."""
    supported = ('md', 'markdown')

    def convert_blocks(self, blocks):
        for block in blocks:
            self.convert_block(block)

    def convert_block(self, block):
        if (block.t == "Document"):
            self.convert_blocks(block.children)
        elif (block.t == "ATXHeader") or (block.t == "SetextHeader"):
            self.section(block)
        elif (block.t == "Paragraph"):
            self.paragraph(block)
        elif (block.t == "BlockQuote"):
            self.blockquote(block)
        elif (block.t == "ListItem"):
            self.list_item(block)
        elif (block.t == "List"):
            self.list_block(block)
        elif (block.t == "IndentedCode"):
            self.verbatim(block.string_content)
        elif (block.t == "FencedCode"):
            if len(block.strings) and len(block.strings[0]):
                self.code(block.strings[0].strip(), block.string_content)
            else:
                self.verbatim(block.string_content)
        elif (block.t == "ReferenceDef"):
            self.reference(block)
        elif (block.t == "HorizontalRule"):
            self.horizontal_rule()
        elif (block.t == "HtmlBlock"):
            self.html_block(block)
        else:
            warn("Unsupported block type: " + block.t)

    def parse(self, inputstring, document):
        self.setup_parse(inputstring, document)

        self.document = document
        self.current_node = document
        self.section_handler = _SectionHandler(document)

        parser = DocParser()

        ast = parser.parse(inputstring + '\n')

        self.convert_block(ast)

        self.finish_parse()

    @contextmanager
    def _temp_current_node(self, current_node):
        saved_node = self.current_node
        self.current_node = current_node
        yield
        self.current_node = saved_node

    # Blocks
    def section(self, block):
        new_section = nodes.section()
        new_section.line = block.start_line
        new_section['level'] = block.level

        title_node = nodes.title()
        title_node.line = block.start_line
        append_inlines(title_node, block.inline_content)
        new_section.append(title_node)
        name = nodes.fully_normalize_name(title_node.astext())
        new_section['names'].append(name)
        self.current_node.document.note_implicit_target(new_section, new_section)
        new_section['ids'].append(nodes.make_id(name))

        self.section_handler.add_new_section(new_section, block.level)
        self.current_node = new_section

    def verbatim(self, text):
        verbatim_node = nodes.literal_block()
        text = ''.join(flatten(text))
        if text.endswith('\n'):
            text = text[:-1]
        verbatim_node.append(nodes.Text(text))
        self.current_node.append(verbatim_node)

    def code(self, language, text):
        node = nodes.literal_block(text, text, language=language)
        self.current_node.append(node)

    def paragraph(self, block):
        p = nodes.paragraph()
        p.line = block.start_line
        append_inlines(p, block.inline_content)
        self.current_node.append(p)

    def blockquote(self, block):
        q = nodes.block_quote()
        q.line = block.start_line

        with self._temp_current_node(q):
            self.convert_blocks(block.children)

        self.current_node.append(q)

    def list_item(self, block):
        node = nodes.list_item()
        node.line = block.start_line

        with self._temp_current_node(node):
            self.convert_blocks(block.children)

        self.current_node.append(node)

    def list_block(self, block):
        list_node = None
        if (block.list_data['type'] == "Bullet"):
            list_node = nodes.bullet_list()
        else:
            list_node = nodes.enumerated_list()
        list_node.line = block.start_line

        with self._temp_current_node(list_node):
            self.convert_blocks(block.children)

        self.current_node.append(list_node)

    def html_block(self, block):
        raw_node = nodes.raw('', block.string_content, format='html')
        raw_node.line = block.start_line
        self.current_node.append(raw_node)

    def horizontal_rule(self):
        transition_node = nodes.transition()
        self.current_node.append(transition_node)

    def reference(self, block):
        target_node = nodes.target()
        target_node.line = block.start_line

        target_node['names'].append(make_refname(block.label))

        target_node['refuri'] = block.destination

        if block.title:
            target_node['title'] = block.title

        self.current_node.append(target_node)


def make_refname(label):
    return text_only(label).lower()


def text_only(nodes):
    return "".join(s.c if s.t == "Str" else text_only(s.children)
                   for s in nodes)

# Inlines


def emph(inlines):
    emph_node = nodes.emphasis()
    append_inlines(emph_node, inlines)
    return emph_node


def strong(inlines):
    strong_node = nodes.strong()
    append_inlines(strong_node, inlines)
    return strong_node


def inline_code(inline):
    literal_node = nodes.literal()
    literal_node.append(nodes.Text(inline.c))
    return literal_node


def inline_html(inline):
    literal_node = nodes.raw('', inline.c, format='html')
    return literal_node


def inline_entity(inline):
    val = HTMLRenderer().renderInline(inline)
    entity_node = nodes.paragraph('', val, format='html')
    return entity_node


def reference(block):
    ref_node = nodes.reference()

    label = make_refname(block.label)

    ref_node['name'] = label
    if block.destination is not None:
        ref_node['refuri'] = block.destination
    else:
        ref_node['refname'] = label
        # self.document.note_refname(ref_node)

    if block.title:
        ref_node['title'] = block.title

    append_inlines(ref_node, block.label)
    return ref_node


def image(block):
    img_node = nodes.image()

    img_node['uri'] = block.destination

    if block.title:
        img_node['title'] = block.title

    img_node['alt'] = text_only(block.label)
    return img_node


def parse_inline(parent_node, inline):
    node = None
    if (inline.t == "Str"):
        node = nodes.Text(inline.c)
    elif (inline.t == "Softbreak"):
        node = nodes.Text('\n')
    elif inline.t == "Emph":
        node = emph(inline.c)
    elif inline.t == "Strong":
        node = strong(inline.c)
    elif inline.t == "Link":
        node = reference(inline)
    elif inline.t == "Image":
        node = image(inline)
    elif inline.t == "Code":
        node = inline_code(inline)
    elif inline.t == "Html":
        node = inline_html(inline)
    elif (inline.t == "Entity"):
        node = inline_entity(inline)
    else:
        warn("Unsupported inline type " + inline.t)
        return
    node.line = inline.start_line
    parent_node.append(node)


def append_inlines(parent_node, inlines):
    for i in range(len(inlines)):
        parse_inline(parent_node, inlines[i])
