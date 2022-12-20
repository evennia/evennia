"""
Outgoing callables to apply with the FuncParser on outgoing messages.

The functions in this module will become available as $funcname(args, kwargs)
in all outgoing strings if you add

    FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED = True

to your settings file. The default inlinefuncs are found at the bottom of
`evennia.utils.funcparser`.

In text, usage is straightforward:

$funcname(arg1, arg2, ..., key=val, key2=val2, ...)

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

    def funcname(*args, **kwargs)
        ...

"""

# def capitalize(*args, **kwargs):
#    "Silly capitalize example. Used as  $capitalize
#    if not args:
#        return ''
#    session = kwargs.get("session")
#    return args[0].capitalize()
