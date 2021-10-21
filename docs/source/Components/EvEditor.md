# EvEditor


Evennia offers a powerful in-game line editor in `evennia.utils.eveditor.EvEditor`. This editor,
mimicking the well-known VI line editor. It offers line-by-line editing, undo/redo, line deletes,
search/replace, fill, dedent and more.

## Launching the editor

The editor is created as follows:

```python
from evennia.utils.eveditor import EvEditor

EvEditor(caller,
         loadfunc=None, savefunc=None, quitfunc=None,
         key="")
```

 - `caller` (Object or Account): The user of the editor.
 - `loadfunc` (callable, optional): This is a function called when the editor is first started. It
is called with `caller` as its only argument. The return value from this function is used as the
starting text in the editor buffer.
 - `savefunc` (callable, optional): This is called when the user saves their buffer in the editor is
called with two arguments, `caller` and `buffer`, where `buffer` is the current buffer.
 - `quitfunc` (callable, optional): This is called when the user quits the editor. If given, all
cleanup and exit messages to the user must be handled by this function.
 - `key` (str, optional): This text will be displayed as an identifier and reminder while editing.
It has no other mechanical function.
 - `persistent` (default `False`): if set to `True`, the editor will survive a reboot.

## Example of usage

This is an example command for setting a specific Attribute using the editor.

```python
from evennia import Command
from evennia.utils import eveditor

class CmdSetTestAttr(Command):
    """
    Set the "test" Attribute using
    the line editor.

    Usage:
       settestattr

    """
    key = "settestattr"
    def func(self):
        "Set up the callbacks and launch the editor"
        def load(caller):
            "get the current value"
            return caller.attributes.get("test")
        def save(caller, buffer):
            "save the buffer"
            caller.attributes.set("test", buffer)
        def quit(caller):
            "Since we define it, we must handle messages"
            caller.msg("Editor exited")
        key = f"{self.caller}/test"
        # launch the editor
        eveditor.EvEditor(self.caller,
                          loadfunc=load, savefunc=save, quitfunc=quit,
                          key=key)
```

## Persistent editor

If you set the `persistent` keyword to `True` when creating the editor, it will remain open even
when reloading the game.  In order to be persistent, an editor needs to have its callback functions
(`loadfunc`, `savefunc` and `quitfunc`) as top-level functions defined in the module.  Since these
functions will be stored, Python will need to find them.

```python
from evennia import Command
from evennia.utils import eveditor

def load(caller):
    "get the current value"
    return caller.attributes.get("test")

def save(caller, buffer):
    "save the buffer"
    caller.attributes.set("test", buffer)

def quit(caller):
    "Since we define it, we must handle messages"
    caller.msg("Editor exited")

class CmdSetTestAttr(Command):
    """
    Set the "test" Attribute using
    the line editor.

    Usage:
       settestattr

    """
    key = "settestattr"
    def func(self):
        "Set up the callbacks and launch the editor"
        key = f"{self.caller}/test"
        # launch the editor
        eveditor.EvEditor(self.caller,
                          loadfunc=load, savefunc=save, quitfunc=quit,
                          key=key, persistent=True)
```

## Line editor usage

The editor mimics the `VIM` editor as best as possible. The below is an excerpt of the return from
the in-editor help command (`:h`).

```
 <txt>  - any non-command is appended to the end of the buffer.
 :  <l> - view buffer or only line <l>
 :: <l> - view buffer without line numbers or other parsing
 :::    - print a ':' as the only character on the line...
 :h     - this help.

 :w     - save the buffer (don't quit)
 :wq    - save buffer and quit
 :q     - quit (will be asked to save if buffer was changed)
 :q!    - quit without saving, no questions asked

 :u     - (undo) step backwards in undo history
 :uu    - (redo) step forward in undo history
 :UU    - reset all changes back to initial state

 :dd <l>     - delete line <n>
 :dw <l> <w> - delete word or regex <w> in entire buffer or on line <l>
 :DD         - clear buffer

 :y  <l>        - yank (copy) line <l> to the copy buffer
 :x  <l>        - cut line <l> and store it in the copy buffer
 :p  <l>        - put (paste) previously copied line directly after <l>
 :i  <l> <txt>  - insert new text <txt> at line <l>. Old line will move down
 :r  <l> <txt>  - replace line <l> with text <txt>
 :I  <l> <txt>  - insert text at the beginning of line <l>
 :A  <l> <txt>  - append text after the end of line <l>

 :s <l> <w> <txt> - search/replace word or regex <w> in buffer or on line <l>

 :f <l>    - flood-fill entire buffer or line <l>
 :fi <l>   - indent entire buffer or line <l>
 :fd <l>   - de-indent entire buffer or line <l>

 :echo - turn echoing of the input on/off (helpful for some clients)

    Legend:
    <l> - line numbers, or range lstart:lend, e.g. '3:7'.
    <w> - one word or several enclosed in quotes.
    <txt> - longer string, usually not needed to be enclosed in quotes.
```

## The EvEditor to edit code

The `EvEditor` is also used to edit some Python code in Evennia.  The `@py` command supports an
`/edit` switch that will open the EvEditor in code mode.  This mode isn't significantly different
from the standard one, except it handles automatic indentation of blocks and a few options to
control this behavior.

- `:<` to remove a level of indentation for the future lines.
- `:+` to add a level of indentation for the future lines.
- `:=` to disable automatic indentation altogether.

Automatic indentation is there to make code editing more simple.  Python needs correct indentation,
not as an aesthetic addition, but as a requirement to determine beginning and ending of blocks.  The
EvEditor will try to guess the next level of indentation.  If you type a block "if", for instance,
the EvEditor will propose you an additional level of indentation at the next line.  This feature
cannot be perfect, however, and sometimes, you will have to use the above options to handle
indentation.

`:=` can be used to turn automatic indentation off completely.  This can be very useful when trying
to paste several lines of code that are already correctly indented, for instance.

To see the EvEditor in code mode, you can use the `@py/edit` command.  Type in your code (on one or
several lines).  You can then use the `:w` option (save without quitting) and the code you have
typed will be executed.  The `:!` will do the same thing.  Executing code while not closing the
editor can be useful if you want to test the code you have typed but add new lines after your test.
