"""
Inlinefunc

Inline functions allow for direct conversion of text users mark in a
special way. Inlinefuncs are deactivated by default. To activate, add

    INLINEFUNC_ENABLED = True

to your settings file. The default inlinefuncs are found in
evennia.utils.inlinefunc.

In text, usage is straightforward:

{funcname([arg1,arg2,...]) text {/funcname

Example 1 (using the "pad" inlinefunc):
    "This is {pad(50,c,-) a center-padded text{/pad of width 50."
    ->
    "This is -------------- a center-padded text--------------- of width 50."

Example 2 (using "pad" and "time" inlinefuncs):
    "The time is {pad(30){time(){/time{/padright now."
    ->
    "The time is         Oct 25, 11:09         right now."

To add more inline functions, add them to this module, using
the following call signature:

    def funcname(text, *args)

where the text is always the part between {funcname(args) and
{/funcname and the *args are taken from the appropriate part of the
call. It is important that the inline function properly clean the
incoming args, checking their type and replacing them with sane
defaults if needed. If impossible to resolve, the unmodified text
should be returned. The inlinefunc should never cause a traceback.

"""

#def capitalize(text, *args):
#    "Silly capitalize example"
#    return text.capitalize()
