# Health Bar

Contribution by Tim Ashley Jenkins, 2017

The function provided in this module lets you easily display visual
bars or meters as a colorful bar instead of just a number. A "health bar"
is merely the most obvious use for this, but the bar is highly customizable
and can be used for any sort of appropriate data besides player health.

Today's players may be more used to seeing statistics like health,
stamina, magic, and etc. displayed as bars rather than bare numerical
values, so using this module to present this data this way may make it
more accessible. Keep in mind, however, that players may also be using
a screen reader to connect to your game, which will not be able to
represent the colors of the bar in any way. By default, the values
represented are rendered as text inside the bar which can be read by
screen readers.

## Usage

No installation, just import and use `display_meter` from this
module:

```python
    from evennia.contrib.rpg.health_bar import display_meter

    # health is 23/100
    health_bar = display_meter(23, 100)
    caller.msg(prompt=health_bar)

```

The health bar will account for current values above the maximum or
below 0, rendering them as a completely full or empty bar with the
values displayed within.



----

<small>This document page is generated from `evennia/contrib/rpg/health_bar/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
