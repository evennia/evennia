# Inline functions 

```{sidebar}
For much more information about inline functions, see the [FuncParser](../Components/FuncParser.md) documentation
```
_Inline functions_, also known as _funcparser functions_ are embedded strings on the form

    $funcname(args, kwargs)

For example

    > say the answer is $eval(24 * 12)!
    You say, "the answer is 288!"

General processing of outgoing strings is disabled by default. To activate inline-function parsing of outgoing strings, add this to your settings file: 

    FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED=True    

Inline functions are provided by the [FuncParser](../Components/FuncParser.md). It is enabled in a few other situations: 

- Processing of [Prototypes](../Components/Prototypes.md); these 'prototypefuncs' allow for prototypes whose values change dynamically upon spawning. For example, you would set `{key: '$choice(["Bo", "Anne", "Tom"])'`  and spawn a random-named character every time.
- Processing of strings to the `msg_contents` method. This allows for [sending different messages depending on who will see them](./Change-Message-Per-Receiver.md).