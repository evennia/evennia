# In-text tags parsed by Evennia

Evennia understands various extra information embedded in text:

- [Colors](./Colors) - Using `|r`, `|n` etc can be used to mark parts of text with a color. The color will 
  become ANSI/XTerm256 color tags for Telnet connections and CSS information for the webclient.
- [Clickable links](./Clickable-Links) - This allows you to provide a text the user can click to execute an
  in-game command. This is on the form `|lc command |lt text |le`.
- [FuncParser callables](../Components/FuncParser) - These are full-fledged function calls on the form `$funcname(args, kwargs)`
  that lead to calls to Python functions. The parser can be run with different available callables in different
  circumstances. The parser is run on all outgoing messages if `settings.FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED=True`
  (disabled by default).
  
```toctree::

   Colors.md
   Clickable-Links.md
   ../Components/FuncParser.md 
```