"""
Health Bar

Contrib - Tim Ashley Jenkins 2017

The function provided in this module lets you easily display visual
bars or meters - "health bar" is merely the most obvious use for this,
though these bars are highly customizable and can be used for any sort
of appropriate data besides player health.

Today's players may be more used to seeing statistics like health,
stamina, magic, and etc. displayed as bars rather than bare numerical
values, so using this module to present this data this way may make it
more accessible. Keep in mind, however, that players may also be using
a screen reader to connect to your game, which will not be able to
represent the colors of the bar in any way. By default, the values
represented are rendered as text inside the bar which can be read by
screen readers.

The health bar will account for current values above the maximum or
below 0, rendering them as a completely full or empty bar with the
values displayed within.
"""


def display_meter(
    cur_value,
    max_value,
    length=30,
    fill_color=["R", "Y", "G"],
    empty_color="B",
    text_color="w",
    align="left",
    pre_text="",
    post_text="",
    show_values=True,
):
    """
    Represents a current and maximum value given as a "bar" rendered with
    ANSI or xterm256 background colors.
    
    Args:
        cur_value (int): Current value to display
        max_value (int): Maximum value to display
    
    Options:
        length (int): Length of meter returned, in characters
        fill_color (list): List of color codes for the full portion
            of the bar, sans any sort of prefix - both ANSI and xterm256
            colors are usable. When the bar is empty, colors toward the
            start of the list will be chosen - when the bar is full, colors
            towards the end are picked. You can adjust the 'weights' of
            the changing colors by adding multiple entries of the same
            color - for example, if you only want the bar to change when
            it's close to empty, you could supply ['R','Y','G','G','G']
        empty_color (str): Color code for the empty portion of the bar.
        text_color (str): Color code for text inside the bar.
        align (str): "left", "right", or "center" - alignment of text in the bar
        pre_text (str): Text to put before the numbers in the bar
        post_text (str): Text to put after the numbers in the bar
        show_values (bool): If true, shows the numerical values represented by
            the bar. It's highly recommended you keep this on, especially if
            there's no info given in pre_text or post_text, as players on screen
            readers will be unable to read the graphical aspect of the bar.
    """
    # Start by building the base string.
    num_text = ""
    if show_values:
        num_text = "%i / %i" % (cur_value, max_value)
    bar_base_str = pre_text + num_text + post_text
    # Cut down the length of the base string if needed
    if len(bar_base_str) > length:
        bar_base_str = bar_base_str[:length]
    # Pad and align the bar base string
    if align == "right":
        bar_base_str = bar_base_str.rjust(length, " ")
    elif align == "center":
        bar_base_str = bar_base_str.center(length, " ")
    else:
        bar_base_str = bar_base_str.ljust(length, " ")

    if max_value < 1:  # Prevent divide by zero
        max_value = 1
    if cur_value < 0:  # Prevent weirdly formatted 'negative bars'
        cur_value = 0
    if cur_value > max_value:  # Display overfull bars correctly
        cur_value = max_value

    # Now it's time to determine where to put the color codes.
    percent_full = float(cur_value) / float(max_value)
    split_index = round(float(length) * percent_full)
    # Determine point at which to split the bar
    split_index = int(split_index)

    # Separate the bar string into full and empty portions
    full_portion = bar_base_str[:split_index]
    empty_portion = bar_base_str[split_index:]

    # Pick which fill color to use based on how full the bar is
    fillcolor_index = float(len(fill_color)) * percent_full
    fillcolor_index = max(0, int(round(fillcolor_index)) - 1)
    fillcolor_code = "|[" + fill_color[fillcolor_index]

    # Make color codes for empty bar portion and text_color
    emptycolor_code = "|[" + empty_color
    textcolor_code = "|" + text_color

    # Assemble the final bar
    final_bar = (
        fillcolor_code
        + textcolor_code
        + full_portion
        + "|n"
        + emptycolor_code
        + textcolor_code
        + empty_portion
        + "|n"
    )

    return final_bar
