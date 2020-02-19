# Evennia Game Index Client

Greg Taylor 2016, Griatch 2020

This is a client for the [Evennia Game Index]
(http://evennia-game-index.appspot.com/), a listing of games built on
Evennia. By listing your game on the index, you make it easy for other
people in the community to discover your creation.

*Note: Since this is still an early experiment, there is no notion of
ownership for a game listing. As a consequence, we rely on the good behavior
of our users in the early goings. If the index is a success, we'll work
on remedying this.*

## Listing your Game

To list your game, go to your game dir and run 

    evennia connections 

Follow the prompts to add details to the listing. Use `evennia reload`. In your log (visible with `evennia --log`
you should see a note that info has been sent to the game index. 

## Detailed settings

If you don't want to use the wizard you can configure your game listing by opening up `server/conf/settings.py` and
 using the following as a starting point:

```python
######################################################################
# Game index
######################################################################

GAME_INDEX_ENABLED = True
GAME_INDEX_LISTING = {
    'game_status': 'pre-alpha',
    # Optional, comment out or remove if N/A
    'game_website': 'http://my-game.com',
    'short_description': 'This is my game. It is fun. You should play it.',
    # Optional but highly recommended. Markdown is supported.
    'long_description': (
        "Hello, there. You silly person.\n\n"
        "This is the start of a new paragraph. Markdown is cool. Isn't this "
        "[neat](http://evennia.com)? My game is best game. Woohoo!\n\n"
        "Time to wrap this up. One final paragraph for the road."
    ),
    'listing_contact': 'me@my-game.com',
    # At minimum, specify this or the web_client_url options. Both is fine, too.
    'telnet_hostname': 'my-game.com',
    'telnet_port': 1234,
    # At minimum, specify this or the telnet_* options. Both is fine, too.
    'web_client_url': 'http://my-game.com/webclient',
}
```

The following section in this README.md will go over all possible values.

At this point, you should be all set! Simply restart your game and check the
server logs for errors. Your listing and some game state will be sent every
half hour.

## Possible GAME_INDEX_LISTING settings

### game_status

Required: **Yes**
Must be one of: 'pre-alpha', 'alpha', 'beta', 'launched'

Describes the current state of your game.

### game_website

Required: No

The URL to your game's website, if you have one.

### short_description

Required: Yes

A short (max of 255 characters) description of your game that will appear
on the main game index page.

### long_description

Required: No

A longer, full-length description or overview of the game.
[Markdown](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet)
and some of the very basic HTML tags are accepted here.

### listing_contact

Required: **Yes**

An email address for us to get in touch with in the event of a listing issue
or backwards-incompatible change.

### telnet_hostname

Required: **Must specify this and telnet_port OR web_client_url**

The hostname that players can telnet into to play your game.

### telnet_port

Required: **Must specify this and telnet_hostname OR web_client_url**

The port that the players can telnet into to play your game.

### web_client_url

Required: **Must specify this OR telnet_hostname + telnet_port**

Full URL to your game's web-based client.

## What information is being reported?

In addition the the details listed in the previous section, we send some
simple usage stats that don't currently get displayed. These will help the
Evennia maintainers get a feel for some technical specifics for games out in
the wild.

## Troubleshooting

### My game doesn't appear on the listing!

If you don't see your game appear on the listing after reloading your server,
check the server logs. You should see some error messages describing what
went wrong.

### I changed my game name and now there are two entries

This is a side-effect of our current, naive implementation in our listing
system. Your old entry will disappear within two hours. Alternatively,
speak up on IRC and someone might be able to manually purge the old entry.
