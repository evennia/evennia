# Clickable links

Evennia supports clickable links for clients that supports it. This marks certain text so it can be clicked by a mouse and either trigger a given Evennia command, or open a URL in an external web browser. To support clickable links, Evennia requires the webclient or an third-party telnet client with [MXP](http://www.zuggsoft.com/zmud/mxp.htm) support (*Note: Evennia only supports clickable links, no other MXP features*).

- `|lc` to start the link, by defining the command to execute.
- `|lu` to start the link, by defining the URL to open.
- `|lt` to continue with the text to show to the user (the link text).
- `|le` to end the link text and the link definition.

All elements must appear in exactly this order to make a valid link. For example, if you have an object with a description 

```
"If you go |lcnorth|ltto the north|le you will find a cottage."
```

This will display as "If you go __to the north__ you will find a cottage." where clicking the link will execute the command `north`. If the client does not support clickable links, only the link text will be shown.

## MXP can be exploited

By default MXP links are only available _from strings provided in code_ (or via a [batch script](../Components/Batch-Processors.md)). You _cannot_ create MXP links from inside the game - the result will not come out as clickable.

This is a security measure. Consider if a user were able to enter clickable links in their description, like this: 

```
|lc give 1000 gold to Bandit |ltClick here to read my backstory! |le
```

This would be executed by the poor player clicking the link, resulting in them paying 1000 gold to the bandit. 

If you think this risk is acceptable, you can remove this protection by adding the following to your settings: 

```
MXP_OUTGOING_ONLY = False
```

## Other settings

Enable / disable MXP overall (default is shown)

```
MXP_ENABLED = True 
```

Make help entries have clickable topics in supported clients 

```
HELP_CLICKABLE_TOPICS = True
```