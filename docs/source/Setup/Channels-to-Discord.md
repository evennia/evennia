# Connect Evennia channels to Discord

[Discord](https://discord.com) is a popular chat service, especially for game
communities. If you have a discord server for your game, you can connect it
to your in-game channels to communicate between in-game and out.

## Configuring Discord

The first thing you'll need is to set up a Discord bot to connect to your game.
Go to the [bot applications](https://discord.com/developers/applications) page and make a new application. You'll need the
"MESSAGE CONTENT" toggle flipped On, and to add your bot token to your settings.

```python
# mygame/server/conf/secret_settings.py
DISCORD_BOT_TOKEN = '<your Discord bot token>'
```

You will also need the `pyopenssl` module, if it isn't already installed.
Install it into your Evennia python environment with 

    pip install pyopenssl

Lastly, enable Discord in your settings

```python
DISCORD_ENABLED = True
```

Start/reload Evennia and log in as a privileged user. You should now have a new
command available: `discord2chan`. Enter `help discord2chan` for an explanation
of its options.

Adding a new channel link is done with the following command:

     discord2chan <evennia_channel> = <discord_channel_id>

The `evennia_channel` argument must be the name of an existing Evennia channel,
and `discord_channel_id` is the full numeric ID of the Discord channel.

> Your bot needs to be added to the correct Discord server with access to the
> channel in order to send or receive messages. This command does NOT verify that
> your bot has Discord permissions!

## Step-By-Step Discord Setup

This section will walk through the entire process of setting up a Discord
connection to your Evennia game, step by step. If you've completed any of the
steps already, feel free to skip to the next.

### Creating a Discord Bot Application

> You will need an active Discord account and admin access to a Discord server
> in order to connect Evennia to it. This assumes you already do.

Make sure you're logged in on the Discord website, then visit
https://discord.com/developers/applications. Click the "New Application"
button in the upper right corner, then enter the name for your new app - the
name of your Evennia game is a good option.

You'll next be brought to the settings page for the new application. Click "Bot"
on the sidebar menu, then "Build-a-Bot" to create your bot account.

**Save the displayed token!** This will be the ONLY time that Discord will allow
you to see that token - if you lose it, you will have to reset it. This token is
how your bot confirms its identity, so it's very important.

Next, add this token to your _secret_ settings.

```python
# file: mygame/server/conf/secret_settings.py

DISCORD_BOT_TOKEN = '<token>'
```

Once that is saved, scroll down the Bot page a little more and find the toggle for
"Message Content Intent". You'll need this to be toggled to ON, or you bot won't
be able to read anyone's messages.

Finally, you can add any additional settings to your new bot account: a display image,
display nickname, bio, etc. You can come back and change these at any time, so
don't worry about it too much now.

### Adding your bot to your server

While still in your new application, click "OAuth2" on the side menu, then "URL
Generator". On this page, you'll generate an invite URL for your app, then visit
that URL to add it to your server.

In the top box, find the checkbox for `bot` and check it: this will make a second
permissions box appear. In that box, you'll want to check off at least the
following boxes:

- Read Messages/View Channels (in "General Permissions")
- Send Messages (in "Text Permissions")

Lastly, scroll down to the bottom of the page and copy the resulting URL. It should
look something like this:

    https://discord.com/api/oauth2/authorize?client_id=55555555555555555&permissions=3072&scope=bot

Visit that link, select the server for your Evennia connection, and confirm.

After the bot is added to your server, you can fine-tune the permissions further
through the usual Discord server administration.

### Activating Discord in Evennia

You'll need to do two additional things with your Evennia game before it can connect
to Discord.

First, install `pyopenssl` to your virtual environment, if you haven't already.

    pip install pyopenssl

Second, enable the Discord integration in your settings file.

```python
# file: server/conf/settings.py
DISCORD_ENABLED = True
```

Start or reload your game to apply the changed settings, then log in as an account
with at least `Developer` permissions and initialize the bot account on Evennia:

    discord2chan/name <your bot name>

The name you assign it can be anything; it will show up in the `who` list for your
game and your game's channels, but is otherwise unused.

Lastly, confirm that it's fully enabled by entering `discord2chan` on its own.
You should receive a message that there are no active connections to Discord.

### Connecting an Evennia channel to a Discord channel

You will need the name of your Evennia channel, and the channel ID for your Discord
channel. The channel ID is the last part of the URL when you visit a channel.

e.g. if the url is `https://discord.com/channels/55555555555555555/12345678901234567890`
then your channel ID is `12345678901234567890`

Link the two channels with the following command:

    discord2chan <evennia channel> = <discord channel id>

The two channels should now relay to each other. Confirm this works by posting a
message on the evennia channel, and another on the Discord channel - they should
both show up on the other end.

> If you don't see any messages coming to or from Discord, make sure that your bot
> has permission to read and send messages and that your application has the
> "Message Content Intents" flag set.

### Further Customization

The help file for `discord2chan` has more information on how to use the command to
customize your relayed messages.

For anything more complex, however, you can create your own child class of
`DiscordBot` and add it to your settings.

```python
# file: mygame/server/conf/settings.py
# EXAMPLE
DISCORD_BOT_CLASS = 'accounts.bots.DiscordBot'
```

> If you had already set up a Discord relay and are changing this, make sure you
> either delete the old bot account in Evennia or change its typeclass or it won't
> take effect.

The core DiscordBot account class has several useful hooks already set up for
processing and relaying channel messages between Discord and Evennia channels,
along with the (unused by default) `direct_msg` hook for processing DMs sent to
the bot on Discord.

Only messages and server updates are processed by default, but the Discord custom
protocol passes all other unprocessed dispatch data on to the Evennia bot account
so you can add additional handling yourself. However, **this integration is not a full library**
and does not document the full range of possible Discord events.