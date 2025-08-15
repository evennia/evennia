# Clickable links

Evennia allows for clickable links in text for clients that supports it. This marks certain text so it can be clicked by a mouse and either trigger a given Evennia command, or open a URL in an external web browser. To see clickable links, the player must use the Evennia webclient or a third-party telnet client with [MXP](http://www.zuggsoft.com/zmud/mxp.htm) support (*Note: Evennia only supports clickable links, no other MXP features*).

Users with clients lacking MXP support will only see the link as normal text.

```{important}
By default, clickable links can _not_ be added from in-game. Trying to do so will have the link come back as normal text. This is a security measure. See [Settings](#settings) for more information.
```

## Click to run a command

```
|lc command |lt text |le
```

Example:

```
"If you go |lcnorth|ltto the north|le you will find a cottage."
```

This will display as "If you go __to the north__ you will find a cottage." where clicking the link will execute the command `north`.

## Click to open an url in a web browser

```
|lu url |lt text |le 
```

Example: 

```
"Omnious |luhttps://mycoolsounds.com/chanting|ltchanting sounds|le are coming from beyond the door."
```

This will show as "Omnious **chanting sounds** are coming from beyond the door", where clicking the link will open the url in a browser if the client supports doing so.

## Settings 

Enable / disable MXP overall (enabled by default).

```
MXP_ENABLED = True 
```

By default help entries have clickable topics. 

```
HELP_CLICKABLE_TOPICS = True
```

By default clickable links are only available _from strings provided in code_ (or via a [batch script](../Components/Batch-Processors.md)). You _cannot_ create clickable links from inside the game - the result will not come out as clickable.

This is a security measure. Consider if a user were able to enter clickable links in their description, like this: 

```
|lc give 1000 gold to Bandit |ltClick here to read my backstory!|le
```

This would be executed by the poor player clicking the link, resulting in them paying 1000 gold to the bandit. 

This is controlled by the following default setting: 

```
MXP_OUTGOING_ONLY = True
```

Only disable this protection if you know your game cannot be exploited in this way. 