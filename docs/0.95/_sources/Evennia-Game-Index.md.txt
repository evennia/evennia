# Evennia Game Index


The [Evennia game index](http://games.evennia.com) is a list of games built or
being built with Evennia. Anyone is allowed to add their game to the index
- also if you have just started development and don't yet accept external
players. It's a chance for us to know you are out there and for you to make us
intrigued about or excited for your upcoming game!

All we ask is that you check so your game-name does not collide with one
already in the list - be nice!

## Connect with the wizard

From your game dir, run

    evennia connections

This will start the Evennia _Connection wizard_. From the menu, select to add
your game to the Evennia Game Index. Follow the prompts and don't forget to
save your new settings in the end. Use `quit` at any time if you change your
mind.

> The wizard will create a new file `mygame/server/conf/connection_settings.py`
> with the settings you chose. This is imported from the end of your main
> settings file and will thus override it. You can edit this new file if you
> want, but remember that if you run the wizard again, your changes may get
> over-written.

## Manual Settings

If you don't want to use the wizard (maybe because you already have the client installed from an
earlier version), you can also configure your index entry in your settings file
(`mygame/server/conf/settings.py`). Add the following:

```python
GAME_INDEX_ENABLED = True

GAME_INDEX_LISTING = {
    # required
    'game_status': 'pre-alpha',            # pre-alpha, alpha, beta, launched
    'listing_contact': "dummy@dummy.com",  # not publicly shown.
    'short_description': 'Short blurb',

    # optional
    'long_description':
        "Longer description that can use Markdown like *bold*, _italic_"
        "and [linkname](http://link.com). Use \n for line breaks."
    'telnet_hostname': 'dummy.com',
    'telnet_port': '1234',
    'web_client_url': 'dummy.com/webclient',
    'game_website': 'dummy.com',
    # 'game_name': 'MyGame',  # set only if different than settings.SERVERNAME
}
```

Of these, the `game_status`, `short_description` and `listing_contact` are
required.  The `listing_contact` is not publicly visible and is only meant as a
last resort if we need to get in touch with you over any listing issue/bug (so
far this has never happened).

If `game_name` is not set, the `settings.SERVERNAME` will be used. Use empty strings
(`''`) for optional fields you don't want to specify at this time.

## Non-public games

If you don't specify neither `telnet_hostname + port` nor
`web_client_url`, the Game index will list your game as _Not yet public_.
Non-public games are moved to the bottom of the index since there is no way
for people to try them out. But it's a good way to show you are out there, even
if you are not ready for players yet.
