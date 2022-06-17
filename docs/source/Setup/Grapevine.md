# Grapevine


[Grapevine](https://grapevine.haus) is a new chat network for `MU*`*** games. By
connecting an in-game channel to the grapevine network, players on your game
can chat with players in other games, also non-Evennia ones.

## Configuring Grapevine

To use Grapevine, you first need the `pyopenssl` module. Install it into your
Evennia python environment with 

    pip install pyopenssl

To configure Grapevine, you'll need to activate it in your settings file. 

```python
    GRAPEVINE_ENABLED = True
```

Next, register an account at https://grapevine.haus. When you have logged in, 
go to your Settings/Profile and to the `Games` sub menu. Here you register your 
new game by filling in its information. At the end of registration you are going
to get a `Client ID` and a `Client Secret`. These should not be shared. 

Open/create the file `mygame/server/conf/secret_settings.py` and add the following:

```python
  GRAPEVINE_CLIENT_ID = "<client ID>"
  GRAPEVINE_CLIENT_SECRET = "<client_secret>"
```

You can also customize the Grapevine channels you are allowed to connect to. This 
is added to the `GRAPEVINE_CHANNELS` setting. You can see which channels are available 
by going to the Grapevine online chat here: https://grapevine.haus/chat.

Start/reload Evennia and log in as a privileged user. You should now have a new
command available: `@grapevine2chan`. This command is called like this:

     @grapevine2chan[/switches] <evennia_channel> = <grapevine_channel>

Here, the `evennia_channel` must be the name of an existing Evennia channel and 
`grapevine_channel` one of the supported channels in `GRAPEVINE_CHANNELS`. 

> At the time of writing, the Grapevine network only has two channels:
> `testing` and `gossip`. Evennia defaults to allowing connecting to both. Use
> `testing` for trying your connection.

## Setting up Grapevine, step by step

You can connect Grapevine to any Evennia channel (so you could connect it to
the default *public* channel if you like), but for testing, let's set up a
new channel `gw`.

     @ccreate gw = This is connected to an gw channel!

You will automatically join the new channel.

Next we will create a connection to the Grapevine network.

     @grapevine2chan gw = gossip

Evennia will now create a new connection and connect it to Grapevine. Connect
to https://grapevine.haus/chat to check. 


Write something in the Evennia channel *gw* and check so a message appears in
the Grapevine chat. Write a reply in the chat and the grapevine bot should echo
it to your channel in-game. 

Your Evennia gamers can now chat with users on external Grapevine channels!
