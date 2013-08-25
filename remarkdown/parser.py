from contextlib import contextmanager
import itertools
import os.path

from docutils import parsers, nodes
import parsley

__all__ = ['MarkdownParser']

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


class MarkdownParser(object, parsers.Parser):
    supported = ('md', 'markdown')

    def parse(self, inputstring, document):
        self.setup_parse(inputstring, document)

        self.document = document
        self.current_node = document
        self.section_handler = _SectionHandler(document)

        base = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(base, "markdown.parsley")

        with open(filename) as pry_file:
            self.grammar_raw = pry_file.read()
        self.grammar = parsley.makeGrammar(
                self.grammar_raw,
                dict(builder=self),
                name='Markdown'
            )

        self.grammar(inputstring + '\n').document()
        self.finish_parse()

    @contextmanager
    def _temp_current_node(self, current_node):
        saved_node = self.current_node
        self.current_node = current_node
        yield
        self.current_node = saved_node

    # Blocks
    def section(self, text, level):
        new_section = nodes.section()
        new_section['level'] = level

        title_node = nodes.title()
        append_inlines(title_node, text)
        new_section.append(title_node)

        self.section_handler.add_new_section(new_section, level)
        self.current_node = new_section

    def verbatim(self, text):
        verbatim_node = nodes.literal_block()
        text = ''.join(flatten(text))
        if text.endswith('\n'):
            text = text[:-1]
        verbatim_node.append(nodes.Text(text))
        self.current_node.append(verbatim_node)

    def paragraph(self, text):
        p = nodes.paragraph()
        append_inlines(p, text)
        self.current_node.append(p)

    def quote(self, text):
        q = nodes.block_quote()

        with self._temp_current_node(q):
            self.grammar(text).document()

        self.current_node.append(q)


    def _build_list(self, items, node):
        for item in items:
            list_item = nodes.list_item()
            with self._temp_current_node(list_item):
                self.grammar(item + "\n\n").document()

            node.append(list_item)
        return node

    def bullet_list(self, items):
        bullet_list = nodes.bullet_list()
        self._build_list(items, bullet_list)
        self.current_node.append(bullet_list)

    def ordered_list(self, items):
        ordered_list = nodes.enumerated_list()
        self._build_list(items, ordered_list)
        self.current_node.append(ordered_list)


    def horizontal_rule(self):
        self.current_node.append(nodes.transition())


    def target(self, label, uri, title):
        target_node = nodes.target()

        target_node['names'].append(make_refname(label))

        target_node['refuri'] = uri

        if title:
            target_node['title'] = title

        self.current_node.append(target_node)


    # Inlines
    def emph(self, inlines):
        emph_node = nodes.emphasis()
        append_inlines(emph_node, inlines)
        return emph_node

    def strong(self, inlines):
        strong_node = nodes.strong()
        append_inlines(strong_node, inlines)
        return strong_node

    def literal(self, inlines):
        literal_node = nodes.literal()
        append_inlines(literal_node, inlines)
        return literal_node

    def reference(self, content, label=None, uri=None, title=None):

        ref_node = nodes.reference()
        label = make_refname(content if label is None else label)

        ref_node['name'] = label
        if uri is not None:
            ref_node['refuri'] = uri
        else:
            ref_node['refname'] = label
            self.document.note_refname(ref_node)

        if title:
            ref_node['title'] = title

        append_inlines(ref_node, content)
        return ref_node


    def image(self, content, label=None, uri=None, title=None):

        label = make_refname(content if label is None else label)
        if uri is not None:
            img_node = nodes.image()
            img_node['uri'] = uri
        else:
            img_node = nodes.substitution_reference()
            img_node['refname'] = label
            self.document.note_refname(img_node)

        if title:
            img_node['title'] = title

        img_node['alt'] = text_only(content)
        return img_node


def _is_string(val):
    return isinstance(val, basestring)

def make_refname(label):
    return text_only(label).lower()

def text_only(nodes):
    return "".join(s if _is_string(s) else text_only(s.children)
                   for s in nodes)

def append_inlines(parent_node, inlines):
    for is_text, elem_group in itertools.groupby(inlines, _is_string):
        if is_text:
            parent_node.append(nodes.Text("".join(elem_group)))
        else:
            map(parent_node.append, elem_group)

