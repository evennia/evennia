# Understanding Color Tags

This tutorial aims at dispelling confusions regarding the use of color tags within Evennia.

Correct understanding of this topic requires having read the [TextTags](TextTags) page and learned Evennia's color tags. Here we'll explain by examples the reasons behind the unexpected (or apparently incoherent) behaviors of some color tags, as mentioned _en passant_ in the [TextTags](TextTags) page.


All you'll need for this tutorial is access to a running instance of Evennia via a color-enabled client. The examples provided are just commands that you can type in your client.

Evennia, ANSI and Xterm256
==========================

All modern MUD clients support colors; nevertheless, the standards to which all clients abide dates back to old day of terminals, and when it comes to colors we are dealing with ANSI and Xterm256 standards.

Evennia handles transparently, behind the scenes, all the code required to enforce these standards—so, if a user connects with a client which doesn't support colors, or supports only ANSI (16 colors), Evennia will take all due steps to ensure that the output will be adjusted to look right at the client side.

As for you, the developer, all you need to care about is knowing how to correctly use the color tags within your MUD. Most likely, you'll be adding colors to help pages, descriptions, automatically generated text, etc.

You are free to mix together ANSI and Xterm256 color tags, but you should be aware of a few pitfalls. ANSI and Xterm256 coexist without conflicts in Evennia, but in many ways they don't «see» each other: ANSI-specific color tags will have no effect on Xterm-defined colors, as we shall see here.

ANSI
====

ANSI has a set of 16 colors, to be more precise: ANSI has 8 basic colors which come in _dark_ and _bright_ flavours—with _dark_ being _normal_. The colors are: red, green, yellow, blue, magenta, cyan, white and black. White in its dark version is usually referred to as gray, and black in its bright version as darkgray. Here, for sake of simplicity they'll be referred to as dark and bright: bright/dark black, bright/dark white.

The default colors of MUD clients is normal (dark) white on normal black (ie: gray on black).

It's important to grasp that in the ANSI standard bright colors apply only to text (foreground), not to background. Evennia allows to bypass this limitation via Xterm256, but doing so will impact the behavior of ANSI tags, as we shall see.

Also, it's important to remember that the 16 ANSI colors are a convention, and the final user can always customize their appearance—he might decide to have green show as red, and dark green as blue, etc.

Xterm256
========

The 16 colors of ANSI should be more than enough to handle simple coloring of text. But when an author wants to be sure that a given color will show as he intended it, she might choose to rely on Xterm256 colors.

Xterm256 doesn't rely on a palette of named colors, it instead represent colors by their values. So, a red color could be `|[500` (bright and pure red), or `|[300` (darker red), and so on.

ANSI Color Tags in Evennia
==========================

>   NOTE: for ease of reading, the examples contain extra white spaces after the
>   color tags (eg: `|g green |b blue` ). This is done only so that it's easier
>   to see the tags separated from their context; it wouldn't be good practice
>   in real-life coding.

Let's proceed by examples. In your MUD client type:


    say Normal |* Negative

Evennia should output the word "Normal" normally (ie: gray on black) and "Negative" in reversed colors (ie: black on gray).

This is pretty straight forward, the `|*` ANSI *invert* tag switches between foreground and background—from now on, **FG** and **BG** shorthands will be used to refer to foreground and background.

But take mental note of this: `|*` has switched *dark white* and *dark black*.

Now try this:

    say |w Bright white FG |* Negative

You'll notice that the word "Negative" is not black on white, it's darkgray on gray. Why is this? Shouldn't it be black text on a white BG? Two things are happening here.

As mentioned, ANSI has 8 base colors, the dark ones. The bright ones are achieved by means of *highlighting* the base/dark/normal colors, and they only apply to FG.

What happened here is that when we set the bright white FG with `|w`, Evennia translated this into the ANSI sequence of Highlight On + White FG. In terms of Evennia's color tags, it's as if we typed:


    say |h|!W Bright white FG |* Negative

Furthermore, the Highlight-On property (which only works for BG!) is preserved after the FG/BG switch, this being the reason why we see black as darkgray: highlighting makes it *bright black* (ie: darkgray).

As for the BG being also grey, that is normal—ie: you are seeing *normal white* (ie: dark white = gray). Remember that since there are no bright BG colors, the ANSI `|*` tag will transpose any FG color in its normal/dark version. So here the FG's bright white became dark white in the BG! In reality, it was always normal/dark white, except that in the FG is seen as bright because of the highlight tag behind the scenes.

Let's try the same thing with some color:

    say |m |[G Bright Magenta on Dark Green |* Negative

Again, the BG stays dark because of ANSI rules, and the FG stays bright because of the implicit `|h` in `|m`.

Now, let's see what happens if we set a bright BG and then invert—yes, Evennia kindly allows us to do it, even if it's not within ANSI expectations.

    say |[b Dark White on Bright Blue |* Negative

Before color inversion, the BG does show in bright blue, and after inversion (as expected) it's *dark white* (gray). The bright blue of the BG survived the inversion and gave us a bright blue FG. This behavior is tricky though, and not as simple as it might look.

If the inversion were to be pure ANSI, the bright blue would have been accounted just as normal blue, and should have converted to normal blue in the FG (after all, there was no highlighting on). The fact is that in reality this color is not bright blue at all, it just an Xterm version of it!

To demonstrate this, type:

    say |[b Dark White on Bright Blue |* Negative |H un-bright

The `|H` Highlight-Off tag should have turned *dark blue* the last word; but it didn't because it couldn't: in order to enforce the non-ANSI bright BG Evennia turned to Xterm, and Xterm entities are not affected by ANSI tags!

So, we are getting at the heart of all confusions and possible odd-behaviors pertaining color tags in Evennia: apart from Evennia's translations from- and to- ANSI/Xterm, the two systems are independent and transparent to each other.

The bright blue of the previous example was just an Xterm representation of the ANSI standard blue. Try to change the default settings of your client, so that blue shows as some other color, you'll then realize the difference when Evennia is sending a true ANSI color (which will show up according to your settings) and when instead it's sending an Xterm representation of that color (which will show up always as defined by Evennia).

You'll have to keep in mind that the presence of an Xterm BG or FG color might affect the way your tags work on the text. For example:

    say |[b Bright Blue BG |* Negative |!Y Dark Yellow |h not bright

Here the `|h` tag no longer affects the FG color. Even though it was changed via the `|!` tag, the ANSI system is out-of-tune because of the intrusion of an Xterm color (bright blue BG, then moved to FG with `|*`).

All unexpected ANSI behaviours are the result of mixing Xterm colors (either on purpose or either via bright BG colors). The `|n` tag will restore things in place and ANSI tags will respond properly again. So, at the end is just an issue of being mindful when using Xterm colors or bright BGs, and avoid wild mixing them with ANSI tags without normalizing (`|n`) things again.

Try this:

    say |[b Bright Blue BG |* Negative |!R Red FG

And then:

    say |[B Dark Blue BG |* Negative |!R Red BG??

In this second example the `|!` changes the BG color instead of the FG! In fact, the odd behavior is the one from the former example, non the latter. When you invert FG and BG with `|*` you actually inverting their references. This is why the last example (which has a normal/dark BG!) allows `|!` to change the BG color. In the first example, it's again the presence of an Xterm color (bright blue BG) which changes the default behavior.

Try this:

`say Normal |* Negative |!R Red BG`

This is the normal behavior, and as you can see it allows `|!` to change BG color after the inversion of FG and BG.

As long as you have an understanding of how ANSI works, it should be easy to handle color tags avoiding the pitfalls of Xterm-ANSI promisquity.

One last example:

`say Normal |* Negative |* still Negative`

Shows that `|*` only works once in a row and will not (and should not!) revert back if used again. Nor it will have any effect until the `|n` tag is called to "reset" ANSI back to normal. This is how it is meant to work.

ANSI operates according to a simple states-based mechanism, and it's important to understand the positive effect of resetting with the `|n` tag, and not try to
push it over the limit, so to speak.
