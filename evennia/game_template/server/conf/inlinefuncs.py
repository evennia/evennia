"""
Inlinefunc

Inline functions allow for direct conversion of text users mark in a
special way. Inlinefuncs are deactivated by default. To activate, add

    INLINEFUNC_ENABLED = True

to your settings file. The default inlinefuncs are found in
evennia.utils.inlinefunc.

In text, usage is straightforward:

$funcname([arg1,[arg2,...]])

Example 1 (using the "pad" inlinefunc):
    say This is $pad("a center-padded text", 50,c,-) of width 50.
    ->
    John says, "This is -------------- a center-padded text--------------- of width 50."

Example 2 (using nested "pad" and "time" inlinefuncs):
    say The time is $pad($time(), 30)right now.
    ->
    John says, "The time is         Oct 25, 11:09         right now."

To add more inline functions, add them to this module, using
the following call signature:

    def funcname(text, *args, **kwargs)

where `text` is always the part between {funcname(args) and
{/funcname and the *args are taken from the appropriate part of the
call. If no {/funcname is given, `text` will be the empty string.

It is important that the inline function properly clean the
incoming `args`, checking their type and replacing them with sane
defaults if needed. If impossible to resolve, the unmodified text
should be returned. The inlinefunc should never cause a traceback.

While the inline function should accept **kwargs, the keyword is
never accepted as a valid call - this is only intended to be used
internally by Evennia, notably to send the `session` keyword to
the function; this is the session of the object viewing the string
and can be used to customize it to each session.

"""

# def capitalize(text, *args, **kwargs):
#    "Silly capitalize example. Used as {capitalize() ... {/capitalize"
#    session = kwargs.get("session")
#    return text.capitalize()
