# Weather Tutorial


This tutorial will have us create a simple weather system for our MUD.  The way we want to use this
is to have all outdoor rooms echo weather-related messages to the room at regular and semi-random
intervals. Things like "Clouds gather above", "It starts to rain" and so on.

One could imagine every outdoor room in the game having a script running on themselves that fires
regularly. For this particular example it is however more efficient to do it another way, namely by
using a "ticker-subscription" model. The principle is simple: Instead of having each Object
individually track the time, they instead subscribe to be called by a global ticker who handles time
keeping.  Not only does this centralize and organize much of the code in one place, it also has less
computing overhead.

Evennia offers the [TickerHandler](../Components/TickerHandler.md) specifically for using the subscription model. We
will use it for our weather system.

We will assume you know how to make your own Typeclasses. If not see one of the beginning tutorials.
We will create a new WeatherRoom typeclass that is aware of the day-night cycle.

```python

    import random
    from evennia import DefaultRoom, TICKER_HANDLER
    
    ECHOES = ["The sky is clear.", 
              "Clouds gather overhead.",
              "It's starting to drizzle.",
              "A breeze of wind is felt.",
              "The wind is picking up"] # etc  

    class WeatherRoom(DefaultRoom):
        "This room is ticked at regular intervals"        
       
        def at_object_creation(self):
            "called only when the object is first created"
            TICKER_HANDLER.add(60 * 60, self.at_weather_update)

        def at_weather_update(self, *args, **kwargs):
            "ticked at regular intervals"
            echo = random.choice(ECHOES)
            self.msg_contents(echo)
```

In the `at_object_creation` method, we simply added ourselves to the TickerHandler and tell it to
call `at_weather_update` every hour (`60*60` seconds). During testing you might want to play with a
shorter time duration.

For this to work we also create a custom hook `at_weather_update(*args, **kwargs)`, which is the
call sign required by TickerHandler hooks.

Henceforth the room will inform everyone inside it when the weather changes. This particular example
is of course very simplistic - the weather echoes are just randomly chosen and don't care what
weather came before it. Expanding it to be more realistic is a useful exercise.