# Tutorial Tweeting Game Stats


This tutorial will create a simple script that will send a tweet to your already configured twitter
account. Please see: [How to connect Evennia to Twitter](../Setup/How-to-connect-Evennia-to-Twitter) if you
haven't already done so.

The script could be expanded to cover a variety of statistics you might wish to tweet about
regularly, from player deaths to how much currency is in the economy etc.

```python
# evennia/typeclasses/tweet_stats.py

import twitter
from random import randint
from django.conf import settings
from evennia import ObjectDB
from evennia import spawner
from evennia import logger
from evennia import DefaultScript

class TweetStats(DefaultScript):
    """
    This implements the tweeting of stats to a registered twitter account
    """

    # standard Script hooks 

    def at_script_creation(self):
        "Called when script is first created"

        self.key = "tweet_stats"
        self.desc = "Tweets interesting stats about the game"
        self.interval = 86400  # 1 day timeout
        self.start_delay = False
        
    def at_repeat(self):
        """
        This is called every self.interval seconds to tweet interesting stats about the game.
        """
        
        api = twitter.Api(consumer_key='consumer_key',
          consumer_secret='consumer_secret',
          access_token_key='access_token_key',
          access_token_secret='access_token_secret')
        
        number_tweet_outputs = 2

        tweet_output = randint(1, number_tweet_outputs)

        if tweet_output == 1:
        ##Game Chars, Rooms, Objects taken from @stats command
            nobjs = ObjectDB.objects.count()
            base_char_typeclass = settings.BASE_CHARACTER_TYPECLASS
            nchars = ObjectDB.objects.filter(db_typeclass_path=base_char_typeclass).count()
            nrooms =
ObjectDB.objects.filter(db_location__isnull=True).exclude(db_typeclass_path=base_char_typeclass).count()
            nexits = ObjectDB.objects.filter(db_location__isnull=False,
db_destination__isnull=False).count()
            nother = nobjs - nchars - nrooms - nexits
            tweet = "Chars: %s, Rooms: %s, Objects: %s" %(nchars, nrooms, nother)
        else: 
            if tweet_output == 2: ##Number of prototypes and 3 random keys - taken from @spawn
command
                prototypes = spawner.spawn(return_prototypes=True)
            
                keys = prototypes.keys()
                nprots = len(prototypes)
                tweet = "Prototype Count: %s  Random Keys: " % nprots

                tweet += " %s" % keys[randint(0,len(keys)-1)]
                for x in range(0,2): ##tweet 3
                    tweet += ", %s" % keys[randint(0,len(keys)-1)]
        # post the tweet 
        try:
            response = api.PostUpdate(tweet)
        except:
            logger.log_trace("Tweet Error: When attempting to tweet %s" % tweet)
```

In the `at_script_creation` method, we configure the script to fire immediately (useful for testing)
and setup the delay (1 day) as well as script information seen when you use `@scripts`

In the `at_repeat` method (which is called immediately and then at interval seconds later) we setup
the Twitter API (just like in the initial configuration of twitter).  numberTweetOutputs is used to
show how many different types of outputs we have (in this case 2).  We then build the tweet based on
randomly choosing between these outputs.

1. Shows the number of Player Characters, Rooms and Other/Objects
2. Shows the number of prototypes currently in the game and then selects 3 random keys to show 

[Scripts Information](../Component/Scripts) will show you how to add it as a Global script, however, for testing
it may be useful to start/stop it quickly from within the game.  Assuming that you create the file
as `mygame/typeclasses/tweet_stats.py` it can be started by using the following command

    @script Here = tweet_stats.TweetStats