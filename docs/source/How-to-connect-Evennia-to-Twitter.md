# How to connect Evennia to Twitter


[Twitter](http://en.wikipedia.org/wiki/twitter) is an online social networking service that enables users to send and read short 280-character messages called "tweets". Following is a short tutorial explaining how to enable users to send tweets from inside Evennia.

## Configuring Twitter

You must first have a Twitter account. Log in and register an App at the [Twitter Dev Site](https://apps.twitter.com/). Make sure you enable access to "write" tweets!

To tweet from Evennia you will need both the "API Token" and the "API secret" strings as well as the "Access Token" and "Access Secret" strings.

Twitter changed their requirements to require a Mobile number on the Twitter account to register new apps with write access.  If you're unable to do this, please see [this Dev post](https://dev.twitter.com/notifications/new-apps-registration) which describes how to get around it.

## Install the twitter python module

To use Twitter you must install the [Twitter](https://pypi.python.org/pypi/twitter) Python module:

```
pip install python-twitter
```

## A basic tweet command

Evennia doesn't have a `tweet` command out of the box so you need to write your own little [Command](./Commands) in order to tweet. If you are unsure about how commands work and how to add them, it can be an idea to go through the [Adding a Command Tutorial](./Adding-Command-Tutorial) before continuing.

You can create the command in a separate command module (something like `mygame/commands/tweet.py`) or together with your other custom commands, as you prefer.  

This is how it can look: 

```python
import twitter
from evennia import Command

# here you insert your unique App tokens
# from the Twitter dev site
TWITTER_API = twitter.Api(consumer_key='api_key',
                          consumer_secret='api_secret',
                          access_token_key='access_token_key',
                          access_token_secret='access_token_secret')

class CmdTweet(Command):
    """
    Tweet a message

    Usage: 
      tweet <message>

    This will send a Twitter tweet to a pre-configured Twitter account.
    A tweet has a maximum length of 280 characters. 
    """

    key = "tweet"
    locks = "cmd:pperm(tweet) or pperm(Developers)"
    help_category = "Comms"

    def func(self):
        "This performs the tweet"
 
        caller = self.caller
        tweet = self.args

        if not tweet:
            caller.msg("Usage: tweet <message>")      
            return
 
        tlen = len(tweet)
        if tlen > 280:
            caller.msg("Your tweet was %i chars long (max 280)." % tlen)
            return

        # post the tweet        
        TWITTER_API.PostUpdate(tweet)

        caller.msg("You tweeted:\n%s" % tweet)
```

Be sure to substitute your own actual API/Access keys and secrets in the appropriate places. 

We default to limiting tweet access to players with `Developers`-level access *or* to those players that have the permission "tweet" (allow individual characters to tweet with `@perm/player playername = tweet`). You may change the [lock](./Locks) as you feel is appropriate. Change the overall permission to `Players` if you want everyone to be able to tweet. 

Now add this command to your default command set (e.g in `mygame/commands/defalt_cmdsets.py`") and reload the server. From now on those with access can simply use `tweet <message>` to see the tweet posted from the game's Twitter account.

## Next Steps

This shows only a basic tweet setup, other things to do could be:

* Auto-Adding the character name to the tweet
* More error-checking of postings
* Changing locks to make tweeting open to more people
* Echo your tweets to an in-game channel

Rather than using an explicit command you can set up a Script to send automatic tweets, for example to post updated game stats. See the [Tweeting Game Stats tutorial](./Tutorial-Tweeting-Game-Stats) for help.
