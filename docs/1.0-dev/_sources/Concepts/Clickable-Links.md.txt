## Clickable links

Evennia supports clickable links for clients that supports it. This marks certain text so it can be
clicked by a mouse and either trigger a given Evennia command, or open a URL in an external web 
browser. To support clickable links, Evennia requires the webclient or an third-party telnet client 
with [MXP](http://www.zuggsoft.com/zmud/mxp.htm) support (*Note: Evennia only supports clickable links, no other MXP features*).

- `|lc` to start the link, by defining the command to execute.
- `|lu` to start the link, by defining the URL to open.
- `|lt` to continue with the text to show to the user (the link text).
- `|le` to end the link text and the link definition.

All elements must appear in exactly this order to make a valid link. For example,

```
"If you go |lcnorth|ltto the north|le you will find a cottage."
```

This will display as "If you go __to the north__ you will find a cottage." where clicking the link
will execute the command `north`. If the client does not support clickable links, only the link text
will be shown.

