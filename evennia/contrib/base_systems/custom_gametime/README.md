# Custom gameime

Contrib by vlgeoff, 2017 - based on Griatch's core original

This reimplements the `evennia.utils.gametime` module but with a _custom_
calendar (unusual number of days per week/month/year etc) for your game world.
Like the original, it allows for scheduling events to happen at given
in-game times, but now taking this custom calendar into account.

## Installation

Import and use this in the same way as you would the normal
`evennia.utils.gametime` module.

Customize the calendar by adding a `TIME_UNITS` dict to your settings (see
example below).


## Usage:

```python
    from evennia.contrib.base_systems import custom_gametime

    gametime = custom_gametime.realtime_to_gametime(days=23)

    # scedule an event to fire every in-game 10 hours
    custom_gametime.schedule(callback, repeat=True, hour=10)

```

The calendar can be customized by adding the `TIME_UNITS` dictionary to your
settings file. This maps unit names to their length, expressed in the smallest
unit. Here's the default as an example:

    TIME_UNITS = {
        "sec": 1,
        "min": 60,
        "hr": 60 * 60,
        "hour": 60 * 60,
        "day": 60 * 60 * 24,
        "week": 60 * 60 * 24 * 7,
        "month": 60 * 60 * 24 * 7 * 4,
        "yr": 60 * 60 * 24 * 7 * 4 * 12,
        "year": 60 * 60 * 24 * 7 * 4 * 12, }

When using a custom calendar, these time unit names are used as kwargs to
the converter functions in this module. Even if your calendar uses other names
for months/weeks etc the system needs the default names internally.
