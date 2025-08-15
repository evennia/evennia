# In-text tags parsed by Evennia
```{toctree}
:maxdepth: 2

Colors.md
Clickable-Links.md
Inline-Functions.md
```

Evennia will parse various special tags and markers embedded in text and convert it dynamically depending on if the data is going in or out of the server.

- _Colors_ - Using `|r`, `|n` etc can be used to mark parts of text with a color. The color will 
  become ANSI/XTerm256 color tags for Telnet connections and CSS information for the webclient.
    ```
    > say Hello, I'm wearing my |rred hat|n today. 
    ```
- _Clickable links_ - This allows you to provide a text the user can click to execute an
  in-game command. This is on the form `|lc command |lt text |le`. Clickable links are generally only parsed in the _outgoing_ direction, since if users could provde them, they could be a potential security problem. To activate,  `MXP_ENABLED=True` must be added to settings (disabled by default).
    ```
    py self.msg("This is a |c look |ltclickable 'look' link|le")
    ```
- _FuncParser callables_ - These are full-fledged function calls on the form `$funcname(args, kwargs)` that lead to calls to Python functions. The parser can be run with different available callables in different circumstances. The parser is run on all outgoing messages if `settings.FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED=True` (disabled by default).
    ```
    > say The answer is $eval(40 + 2)! 
    ```


