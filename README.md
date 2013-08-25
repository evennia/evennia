# remarkdown, a markdown parser based on `docutils`

**Note that this code is still alpha, some markdown features might not work yet**

## Why another markdown library?

remarkdown is not just only another markdown library. It mostly contains a parser
that outputs a [`docutils` document tree][docutils]. The different scripts
bundled then use `docutils` for generation of different types of documents.

Why is this important? Many python tools (mostly for documentation creation)
rely on `docutils`. But `docutils` only supports a ReStructuredText syntax. For
instance [this issue][sphinx-issue] and [this StackOverflow
question][so-question] show that there is an interest in allowing `docutils` to
use markdown as an alternative syntax.

[docutils]: http://docutils.sourceforge.net/docs/ref/doctree.html
[sphinx-issue]: https://bitbucket.org/birkenfeld/sphinx/issue/825/markdown-capable-sphinx
[so-question]: http://stackoverflow.com/questions/2471804/using-sphinx-with-markdown-instead-of-rst

## Acknowledgement

The remarkdown PEG is heavily inspired by [peg-markdown by John
MacFarlane][peg-md].


[peg-md]: https://github.com/jgm/peg-markdown


