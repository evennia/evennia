# Things to remember about the flat API

The flat API is a series of 'shortcuts' on the `evennia` main library root (defined in 
`evennia/__init__.py`). Its componentas are documented [as part of the auto-documentation](../Evennia-API.md).

## To remember when importing from `evennia`

Properties on the root of the `evennia` package are *not* modules in their own right. They are just
shortcut properties stored in the `evennia/__init__.py` module. That means that you cannot use dot-
notation to `import` nested module-names over `evennia`. The rule of thumb is that you cannot use
`import` for more than one level down. Hence you can do

```python
    import evennia
    print(evennia.default_cmds.CmdLook)
```

or import one level down

```python
    from evennia import default_cmds
    print(default_cmds.CmdLook)
```

but you *cannot* import two levels down

```python
     from evennia.default_cmds import CmdLook # error!
```

This will give you an `ImportError` telling you that the module `default_cmds` cannot be found -
this is becasue `default_cmds` is just a *variable* stored in `evennia.__init__.py`; this cannot be
imported from. If you really want full control over which level of package you import you can always
bypass the root package and import directly from from the real location. For example
`evennia.DefaultObject` is a shortcut to `evennia.objects.objects.DefaultObject`. Using this full
path will have the import mechanism work normally. See `evennia/__init__.py` to see where the
package imports from.