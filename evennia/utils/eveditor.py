"""
EvEditor (Evennia Line Editor)

This implements an advanced line editor for editing longer texts in-game. The
editor mimics the command mechanisms of the "VI" editor (a famous line-by-line
editor) as far as reasonable.

Features of the editor:

- undo/redo.
- edit/replace on any line of the buffer.
- search&replace text anywhere in buffer.
- formatting of buffer, or selection, to certain width + indentations.
- allow to echo the input or not, depending on your client.
- in-built help

To use the editor, just import EvEditor from this module and initialize it:

```python
from evennia.utils.eveditor import EvEditor

# set up an editor to edit the caller's 'desc' Attribute
def _loadfunc(caller):
    return caller.db.desc

def _savefunc(caller, buffer):
    caller.db.desc = buffer.strip()
    return True

def _quitfunc(caller):
    caller.msg("Custom quit message")

# start the editor
EvEditor(caller, loadfunc=None, savefunc=None, quitfunc=None, key="",
         persistent=True, code=False)
```

The editor can also be used to format Python code and be made to
survive a reload. See the `EvEditor` class for more details.

"""
import re

from django.conf import settings
from django.utils.translation import gettext as _

from evennia import CmdSet
from evennia.commands import cmdhandler
from evennia.utils import dedent, fill, is_iter, justify, logger, to_str, utils
from evennia.utils.ansi import raw

# we use cmdhandler instead of evennia.syscmdkeys to
# avoid some cases of loading before evennia init'd
_CMD_NOMATCH = cmdhandler.CMD_NOMATCH
_CMD_NOINPUT = cmdhandler.CMD_NOINPUT

_RE_GROUP = re.compile(r"\".*?\"|\'.*?\'|\S*")
_COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)
# use NAWS in the future?
_DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH

# -------------------------------------------------------------
#
# texts
#
# -------------------------------------------------------------

_HELP_TEXT = _(
    """
 <txt>  - any non-command is appended to the end of the buffer.
 :  <l> - view buffer or only line(s) <l>
 :: <l> - raw-view buffer or only line(s) <l>
 :::    - escape - enter ':' as the only character on the line.
 :h     - this help.

 :w     - save the buffer (don't quit)
 :wq    - save buffer and quit
 :q     - quit (will be asked to save if buffer was changed)
 :q!    - quit without saving, no questions asked

 :u     - (undo) step backwards in undo history
 :uu    - (redo) step forward in undo history
 :UU    - reset all changes back to initial state

 :dd <l>     - delete last line or line(s) <l>
 :dw <l> <w> - delete word or regex <w> in entire buffer or on line <l>
 :DD         - clear entire buffer

 :y  <l>        - yank (copy) line(s) <l> to the copy buffer
 :x  <l>        - cut line(s) <l> and store it in the copy buffer
 :p  <l>        - put (paste) previously copied line(s) directly after <l>
 :i  <l> <txt>  - insert new text <txt> at line <l>. Old line will move down
 :r  <l> <txt>  - replace line <l> with text <txt>
 :I  <l> <txt>  - insert text at the beginning of line <l>
 :A  <l> <txt>  - append text after the end of line <l>

 :s <l> <w> <txt> - search/replace word or regex <w> in buffer or on line <l>

 :j <l> <w> - justify buffer or line <l>. <w> is f, c, l or r. Default f (full)
 :f <l>     - flood-fill entire buffer or line <l>: Equivalent to :j left
 :fi <l>    - indent entire buffer or line <l>
 :fd <l>    - de-indent entire buffer or line <l>

 :echo - turn echoing of the input on/off (helpful for some clients)
"""
)

_HELP_LEGEND = _(
    """
    Legend:
    <l>   - line number, like '5' or range, like '3:7'.
    <w>   - a single word, or multiple words with quotes around them.
    <txt> - longer string, usually not needing quotes.
"""
)

_HELP_CODE = _(
    """
 :!    - Execute code buffer without saving
 :<    - Decrease the level of automatic indentation for the next lines
 :>    - Increase the level of automatic indentation for the next lines
 :=    - Switch automatic indentation on/off
""".lstrip(
        "\n"
    )
)

_ERROR_LOADFUNC = _(
    """
{error}

|rBuffer load function error. Could not load initial data.|n
"""
)

_ERROR_SAVEFUNC = _(
    """
{error}

|rSave function returned an error. Buffer not saved.|n
"""
)

_ERROR_NO_SAVEFUNC = _("|rNo save function defined. Buffer cannot be saved.|n")

_MSG_SAVE_NO_CHANGE = _("No changes need saving")
_DEFAULT_NO_QUITFUNC = _("Exited editor.")

_ERROR_QUITFUNC = _(
    """
{error}

|rQuit function gave an error. Skipping.|n
"""
)

_ERROR_PERSISTENT_SAVING = _(
    """
{error}

|rThe editor state could not be saved for persistent mode. Switching
to non-persistent mode (which means the editor session won't survive
an eventual server reload - so save often!)|n
"""
)

_TRACE_PERSISTENT_SAVING = _(
    "EvEditor persistent-mode error. Commonly, this is because one or "
    "more of the EvEditor callbacks could not be pickled, for example "
    "because it's a class method or is defined inside another function."
)


_MSG_NO_UNDO = _("Nothing to undo.")
_MSG_NO_REDO = _("Nothing to redo.")
_MSG_UNDO = _("Undid one step.")
_MSG_REDO = _("Redid one step.")

# -------------------------------------------------------------
#
# Handle yes/no quit question
#
# -------------------------------------------------------------


class CmdSaveYesNo(_COMMAND_DEFAULT_CLASS):
    """
    Save the editor state on quit. This catches
    nomatches (defaults to Yes), and avoid saves only if
    command was given specifically as "no" or "n".
    """

    key = _CMD_NOMATCH
    aliases = _CMD_NOINPUT
    locks = "cmd:all()"
    help_cateogory = "LineEditor"

    def func(self):
        """
        Implement the yes/no choice.

        """
        # this is only called from inside the lineeditor
        # so caller.ndb._lineditor must be set.

        self.caller.cmdset.remove(SaveYesNoCmdSet)
        if self.raw_string.strip().lower() in ("no", "n"):
            # answered no
            self.caller.msg(self.caller.ndb._eveditor.quit())
        else:
            # answered yes (default)
            self.caller.ndb._eveditor.save_buffer()
            self.caller.ndb._eveditor.quit()


class SaveYesNoCmdSet(CmdSet):
    """
    Stores the yesno question

    """

    key = "quitsave_yesno"
    priority = 150  # override other cmdsets.
    mergetype = "Replace"

    def at_cmdset_creation(self):
        """at cmdset creation"""
        self.add(CmdSaveYesNo())


# -------------------------------------------------------------
#
# Editor commands
#
# -------------------------------------------------------------


class CmdEditorBase(_COMMAND_DEFAULT_CLASS):
    """
    Base parent for editor commands
    """

    locks = "cmd:all()"
    help_entry = "LineEditor"

    editor = None

    def parse(self):
        """
        Handles pre-parsing. Editor commands are on the form

        ::

            :cmd [li] [w] [txt]

        Where all arguments are optional.

        - `li`  - line number (int), starting from 1. This could also
              be a range given as <l>:<l>.
        - `w`  - word(s) (string), could be encased in quotes.
        - `txt` - extra text (string), could be encased in quotes.

        """

        editor = self.caller.ndb._eveditor
        if not editor:
            # this will completely replace the editor
            _load_editor(self.caller)
            editor = self.caller.ndb._eveditor
        self.editor = editor

        linebuffer = self.editor.get_buffer().split("\n")

        nlines = len(linebuffer)

        # The regular expression will split the line by whitespaces,
        # stripping extra whitespaces, except if the text is
        # surrounded by single- or double quotes, in which case they
        # will be kept together and extra whitespace preserved. You
        # can input quotes on the line by alternating single and
        # double quotes.
        arglist = [part for part in _RE_GROUP.findall(self.args) if part]
        temp = []
        for arg in arglist:
            # we want to clean the quotes, but only one type,
            # in case we are nesting.
            if arg.startswith('"'):
                arg.strip('"')
            elif arg.startswith("'"):
                arg.strip("'")
            temp.append(arg)
        arglist = temp

        # A dumb split, without grouping quotes
        words = self.args.split()

        # current line number
        cline = nlines - 1

        # the first argument could also be a range of line numbers, on the
        # form <lstart>:<lend>. Either of the ends could be missing, to
        # mean start/end of buffer respectively.

        lstart, lend = cline, cline + 1
        linerange = False
        if arglist and arglist[0].count(":") == 1:
            part1, part2 = arglist[0].split(":")
            if part1 and part1.isdigit():
                lstart = min(max(0, int(part1)) - 1, nlines)
                linerange = True
            if part2 and part2.isdigit():
                lend = min(lstart + 1, int(part2)) + 1
                linerange = True
        elif arglist and arglist[0].isdigit():
            lstart = min(max(0, int(arglist[0]) - 1), nlines)
            lend = lstart + 1
            linerange = True
        if linerange:
            arglist = arglist[1:]

        # nicer output formatting of the line range.
        lstr = (
            "line %i" % (lstart + 1)
            if not linerange or lstart + 1 == lend
            else "lines %i-%i" % (lstart + 1, lend)
        )

        # arg1 and arg2 is whatever arguments. Line numbers or -ranges are
        # never included here.
        args = " ".join(arglist)
        arg1, arg2 = "", ""
        if len(arglist) > 1:
            arg1, arg2 = arglist[0], " ".join(arglist[1:])
        else:
            arg1 = " ".join(arglist)

        # store for use in func()

        self.linebuffer = linebuffer
        self.nlines = nlines
        self.arglist = arglist
        self.cline = cline
        self.lstart = lstart
        self.lend = lend
        self.linerange = linerange
        self.lstr = lstr
        self.words = words
        self.args = args
        self.arg1 = arg1
        self.arg2 = arg2


def _load_editor(caller):
    """
    Load persistent editor from storage.

    """
    saved_options = caller.attributes.get("_eveditor_saved")
    saved_buffer, saved_undo = caller.attributes.get("_eveditor_buffer_temp", (None, None))
    unsaved = caller.attributes.get("_eveditor_unsaved", False)
    indent = caller.attributes.get("_eveditor_indent", 0)
    if saved_options:
        eveditor = EvEditor(caller, **saved_options[0])
        if saved_buffer:
            # we have to re-save the buffer data so we can handle subsequent restarts
            caller.attributes.add("_eveditor_buffer_temp", (saved_buffer, saved_undo))
            setattr(eveditor, "_buffer", saved_buffer)
            setattr(eveditor, "_undo_buffer", saved_undo)
            setattr(eveditor, "_undo_pos", len(saved_undo) - 1)
            setattr(eveditor, "_unsaved", unsaved)
            setattr(eveditor, "_indent", indent)
        for key, value in saved_options[1].items():
            setattr(eveditor, key, value)
    else:
        # something went wrong. Cleanup.
        caller.cmdset.remove(EvEditorCmdSet)


class CmdLineInput(CmdEditorBase):
    """
    No command match - Inputs line of text into buffer.

    """

    key = _CMD_NOMATCH
    aliases = _CMD_NOINPUT

    def func(self):
        """
        Adds the line without any formatting changes.

        If the editor handles code, it might add automatic
        indentation.
        """
        caller = self.caller
        editor = caller.ndb._eveditor
        buf = editor.get_buffer()

        # add a line of text to buffer
        line = self.raw_string.strip("\r\n")
        if editor._codefunc and editor._indent >= 0:
            # if automatic indentation is active, add spaces
            line = editor.deduce_indent(line, buf)
        buf = line if not buf else buf + "\n%s" % line
        self.editor.update_buffer(buf)
        if self.editor._echo_mode:
            # need to do it here or we will be off one line
            cline = len(self.editor.get_buffer().split("\n"))
            if editor._codefunc:
                # display the current level of identation
                indent = editor._indent
                if indent < 0:
                    indent = "off"

                self.caller.msg("|b%02i|||n (|g%s|n) %s" % (cline, indent, raw(line)))
            else:
                self.caller.msg("|b%02i|||n %s" % (cline, raw(self.args)))


class CmdEditorGroup(CmdEditorBase):
    """
    Commands for the editor
    """

    key = ":editor_command_group"
    aliases = [
        ":",
        "::",
        ":::",
        ":h",
        ":w",
        ":wq",
        ":q",
        ":q!",
        ":u",
        ":uu",
        ":UU",
        ":dd",
        ":dw",
        ":DD",
        ":y",
        ":x",
        ":p",
        ":i",
        ":j",
        ":r",
        ":I",
        ":A",
        ":s",
        ":S",
        ":f",
        ":fi",
        ":fd",
        ":echo",
        ":!",
        ":<",
        ":>",
        ":=",
    ]
    arg_regex = r"\s.*?|$"

    def func(self):
        """
        This command handles all the in-editor :-style commands. Since
        each command is small and very limited, this makes for a more
        efficient presentation.

        """
        caller = self.caller
        editor = caller.ndb._eveditor

        linebuffer = self.linebuffer
        lstart, lend = self.lstart, self.lend
        cmd = self.cmdstring
        echo_mode = self.editor._echo_mode

        if cmd == ":":
            # Echo buffer
            if self.linerange:
                buf = linebuffer[lstart:lend]
                editor.display_buffer(buf=buf, offset=lstart)
            else:
                editor.display_buffer()
        elif cmd == "::":
            # Echo buffer without the line numbers and syntax parsing
            if self.linerange:
                buf = linebuffer[lstart:lend]
                editor.display_buffer(buf=buf, offset=lstart, linenums=False, options={"raw": True})
            else:
                editor.display_buffer(linenums=False, options={"raw": True})
        elif cmd == ":::":
            # Insert single colon alone on a line
            editor.update_buffer([":"] if lstart == 0 else linebuffer + [":"])
            if echo_mode:
                caller.msg(_("Single ':' added to buffer."))
        elif cmd == ":h":
            # help entry
            editor.display_help()
        elif cmd == ":w":
            # save without quitting
            editor.save_buffer()
        elif cmd == ":wq":
            # save and quit
            editor.save_buffer()
            editor.quit()
        elif cmd == ":q":
            # quit. If not saved, will ask
            if self.editor._unsaved:
                caller.cmdset.add(SaveYesNoCmdSet)
                caller.msg(_("Save before quitting?") + " |lcyes|lt[Y]|le/|lcno|ltN|le")
            else:
                editor.quit()
        elif cmd == ":q!":
            # force quit, not checking saving
            editor.quit()
        elif cmd == ":u":
            # undo
            editor.update_undo(-1)
        elif cmd == ":uu":
            # redo
            editor.update_undo(1)
        elif cmd == ":UU":
            # reset buffer
            editor.update_buffer(editor._pristine_buffer)
            caller.msg(_("Reverted all changes to the buffer back to original state."))
        elif cmd == ":dd":
            # :dd <l> - delete line <l>
            buf = linebuffer[:lstart] + linebuffer[lend:]
            editor.update_buffer(buf)
            caller.msg(_("Deleted {string}.").format(string=self.lstr))
        elif cmd == ":dw":
            # :dw <w> - delete word in entire buffer
            # :dw <l> <w> delete word only on line(s) <l>
            if not self.arg1:
                caller.msg(_("You must give a search word to delete."))
            else:
                if not self.linerange:
                    lstart = 0
                    lend = self.cline + 1
                    caller.msg(
                        _("Removed {arg1} for lines {l1}-{l2}.").format(
                            arg1=self.arg1, l1=lstart + 1, l2=lend + 1
                        )
                    )
                else:
                    caller.msg(
                        _("Removed {arg1} for {line}.").format(arg1=self.arg1, line=self.lstr)
                    )
                sarea = "\n".join(linebuffer[lstart:lend])
                sarea = re.sub(r"%s" % self.arg1.strip("'").strip('"'), "", sarea, re.MULTILINE)
                buf = linebuffer[:lstart] + sarea.split("\n") + linebuffer[lend:]
                editor.update_buffer(buf)
        elif cmd == ":DD":
            # clear buffer
            editor.update_buffer("")

            # Reset indentation level to 0
            if editor._codefunc:
                if editor._indent >= 0:
                    editor._indent = 0
                    if editor._persistent:
                        caller.attributes.add("_eveditor_indent", 0)
            caller.msg(_("Cleared {nlines} lines from buffer.").format(nlines=self.nlines))
        elif cmd == ":y":
            # :y <l> - yank line(s) to copy buffer
            cbuf = linebuffer[lstart:lend]
            editor._copy_buffer = cbuf
            caller.msg(_("{line}, {cbuf} yanked.").format(line=self.lstr.capitalize(), cbuf=cbuf))
        elif cmd == ":x":
            # :x <l> - cut line to copy buffer
            cbuf = linebuffer[lstart:lend]
            editor._copy_buffer = cbuf
            buf = linebuffer[:lstart] + linebuffer[lend:]
            editor.update_buffer(buf)
            caller.msg(_("{line}, {cbuf} cut.").format(line=self.lstr.capitalize(), cbuf=cbuf))
        elif cmd == ":p":
            # :p <l> paste line(s) from copy buffer
            if not editor._copy_buffer:
                caller.msg(_("Copy buffer is empty."))
            else:
                buf = linebuffer[:lstart] + editor._copy_buffer + linebuffer[lstart:]
                editor.update_buffer(buf)
                caller.msg(
                    _("Pasted buffer {cbuf} to {line}.").format(
                        cbuf=editor._copy_buffer, line=self.lstr
                    )
                )
        elif cmd == ":i":
            # :i <l> <txt> - insert new line
            new_lines = self.args.split("\n")
            if not new_lines:
                caller.msg(_("You need to enter a new line and where to insert it."))
            else:
                buf = linebuffer[:lstart] + new_lines + linebuffer[lstart:]
                editor.update_buffer(buf)
                caller.msg(
                    _("Inserted {num} new line(s) at {line}.").format(
                        num=len(new_lines), line=self.lstr
                    )
                )
        elif cmd == ":r":
            # :r <l> <txt> - replace lines
            new_lines = self.args.split("\n")
            if not new_lines:
                caller.msg(_("You need to enter a replacement string."))
            else:
                buf = linebuffer[:lstart] + new_lines + linebuffer[lend:]
                editor.update_buffer(buf)
                caller.msg(
                    _("Replaced {num} line(s) at {line}.").format(
                        num=len(new_lines), line=self.lstr
                    )
                )
        elif cmd == ":I":
            # :I <l> <txt> - insert text at beginning of line(s) <l>
            if not self.raw_string and not editor._codefunc:
                caller.msg(_("You need to enter text to insert."))
            else:
                buf = (
                    linebuffer[:lstart]
                    + ["%s%s" % (self.args, line) for line in linebuffer[lstart:lend]]
                    + linebuffer[lend:]
                )
                editor.update_buffer(buf)
                caller.msg(_("Inserted text at beginning of {line}.").format(line=self.lstr))
        elif cmd == ":A":
            # :A <l> <txt> - append text after end of line(s)
            if not self.args:
                caller.msg(_("You need to enter text to append."))
            else:
                buf = (
                    linebuffer[:lstart]
                    + ["%s%s" % (line, self.args) for line in linebuffer[lstart:lend]]
                    + linebuffer[lend:]
                )
                editor.update_buffer(buf)
                caller.msg(_("Appended text to end of {line}.").format(line=self.lstr))
        elif cmd == ":s":
            # :s <li> <w> <txt> - search and replace words
            # in entire buffer or on certain lines
            if not self.arg1 or not self.arg2:
                caller.msg(_("You must give a search word and something to replace it with."))
            else:
                if not self.linerange:
                    lstart = 0
                    lend = self.cline + 1
                    caller.msg(
                        _("Search-replaced {arg1} -> {arg2} for lines {l1}-{l2}.").format(
                            arg1=self.arg1, arg2=self.arg2, l1=lstart + 1, l2=lend
                        )
                    )
                else:
                    caller.msg(
                        _("Search-replaced {arg1} -> {arg2} for {line}.").format(
                            arg1=self.arg1, arg2=self.arg2, line=self.lstr
                        )
                    )
                sarea = "\n".join(linebuffer[lstart:lend])

                regex = r"%s|^%s(?=\s)|(?<=\s)%s(?=\s)|^%s$|(?<=\s)%s$"
                regarg = self.arg1.strip("'").strip('"')
                if " " in regarg:
                    regarg = regarg.replace(" ", " +")
                sarea = re.sub(
                    regex % (regarg, regarg, regarg, regarg, regarg),
                    self.arg2.strip("'").strip('"'),
                    sarea,
                    re.MULTILINE,
                )
                buf = linebuffer[:lstart] + sarea.split("\n") + linebuffer[lend:]
                editor.update_buffer(buf)
        elif cmd == ":f":
            # :f <l> flood-fill buffer or <l> lines of buffer.
            width = _DEFAULT_WIDTH
            if not self.linerange:
                lstart = 0
                lend = self.cline + 1
                caller.msg(_("Flood filled lines {l1}-{l2}.").format(l1=lstart + 1, l2=lend))
            else:
                caller.msg(_("Flood filled {line}.").format(line=self.lstr))
            fbuf = "\n".join(linebuffer[lstart:lend])
            fbuf = fill(fbuf, width=width)
            buf = linebuffer[:lstart] + fbuf.split("\n") + linebuffer[lend:]
            editor.update_buffer(buf)
        elif cmd == ":j":
            # :f <l> <w>  justify buffer of <l> with <w> as align (one of
            # f(ull), c(enter), r(ight) or l(left). Default is full.
            align_map = {
                "full": "f",
                "f": "f",
                "center": "c",
                "c": "c",
                "right": "r",
                "r": "r",
                "left": "l",
                "l": "l",
            }
            align_name = {"f": "Full", "c": "Center", "l": "Left", "r": "Right"}
            width = _DEFAULT_WIDTH
            if self.arg1 and self.arg1.lower() not in align_map:
                self.caller.msg(
                    _("Valid justifications are")
                    + " [f]ull (default), [c]enter, [r]right or [l]eft"
                )
                return
            align = align_map[self.arg1.lower()] if self.arg1 else "f"
            if not self.linerange:
                lstart = 0
                lend = self.cline + 1
                self.caller.msg(
                    _("{align}-justified lines {l1}-{l2}.").format(
                        align=align_name[align], l1=lstart + 1, l2=lend
                    )
                )
            else:
                self.caller.msg(
                    _("{align}-justified {line}.").format(align=align_name[align], line=self.lstr)
                )
            jbuf = "\n".join(linebuffer[lstart:lend])
            jbuf = justify(jbuf, width=width, align=align)
            buf = linebuffer[:lstart] + jbuf.split("\n") + linebuffer[lend:]
            editor.update_buffer(buf)
        elif cmd == ":fi":
            # :fi <l> indent buffer or lines <l> of buffer.
            indent = " " * 4
            if not self.linerange:
                lstart = 0
                lend = self.cline + 1
                caller.msg(_("Indented lines {l1}-{l2}.").format(l1=lstart + 1, l2=lend))
            else:
                caller.msg(_("Indented {line}.").format(line=self.lstr))
            fbuf = [indent + line for line in linebuffer[lstart:lend]]
            buf = linebuffer[:lstart] + fbuf + linebuffer[lend:]
            editor.update_buffer(buf)
        elif cmd == ":fd":
            # :fi <l> indent buffer or lines <l> of buffer.
            if not self.linerange:
                lstart = 0
                lend = self.cline + 1
                caller.msg(
                    _("Removed left margin (dedented) lines {l1}-{l2}.").format(
                        l1=lstart + 1, l2=lend
                    )
                )
            else:
                caller.msg(_("Removed left margin (dedented) {line}.").format(line=self.lstr))
            fbuf = "\n".join(linebuffer[lstart:lend])
            fbuf = dedent(fbuf)
            buf = linebuffer[:lstart] + fbuf.split("\n") + linebuffer[lend:]
            editor.update_buffer(buf)
        elif cmd == ":echo":
            # set echoing on/off
            editor._echo_mode = not editor._echo_mode
            caller.msg(_("Echo mode set to {mode}").format(mode=editor._echo_mode))
        elif cmd == ":!":
            if editor._codefunc:
                editor._codefunc(caller, editor._buffer)
            else:
                caller.msg(_("This command is only available in code editor mode."))
        elif cmd == ":<":
            # :<
            if editor._codefunc:
                editor.decrease_indent()
                indent = editor._indent
                if indent >= 0:
                    caller.msg(
                        _("Decreased indentation: new indentation is {indent}.").format(
                            indent=indent
                        )
                    )
                else:
                    caller.msg(_("|rManual indentation is OFF.|n Use := to turn it on."))
            else:
                caller.msg(_("This command is only available in code editor mode."))
        elif cmd == ":>":
            # :>
            if editor._codefunc:
                editor.increase_indent()
                indent = editor._indent
                if indent >= 0:
                    caller.msg(
                        _("Increased indentation: new indentation is {indent}.").format(
                            indent=indent
                        )
                    )
                else:
                    caller.msg(_("|rManual indentation is OFF.|n Use := to turn it on."))
            else:
                caller.msg(_("This command is only available in code editor mode."))
        elif cmd == ":=":
            # :=
            if editor._codefunc:
                editor.swap_autoindent()
                indent = editor._indent
                if indent >= 0:
                    caller.msg(_("Auto-indentation turned on."))
                else:
                    caller.msg(_("Auto-indentation turned off."))
            else:
                caller.msg(_("This command is only available in code editor mode."))


class EvEditorCmdSet(CmdSet):
    """CmdSet for the editor commands"""

    key = "editorcmdset"
    mergetype = "Replace"

    def at_cmdset_creation(self):
        self.add(CmdLineInput())
        self.add(CmdEditorGroup())


# -------------------------------------------------------------
#
# Main Editor object
#
# -------------------------------------------------------------


class EvEditor:
    """
    This defines a line editor object. It creates all relevant commands
    and tracks the current state of the buffer. It also cleans up after
    itself.

    """

    def __init__(
        self,
        caller,
        loadfunc=None,
        savefunc=None,
        quitfunc=None,
        key="",
        persistent=False,
        codefunc=False,
    ):
        """
        Launches a full in-game line editor, mimicking the functionality of VIM.

        Args:
            caller (Object): Who is using the editor.
            loadfunc (callable, optional): This will be called as
                `loadfunc(caller)` when the editor is first started. Its
                return will be used as the editor's starting buffer.
            savefunc (callable, optional): This will be called as
                `savefunc(caller, buffer)` when the save-command is given and
                is used to actually determine where/how result is saved.
                It should return `True` if save was successful and also
                handle any feedback to the user.
            quitfunc (callable, optional): This will optionally be
                called as `quitfunc(caller)` when the editor is
                exited. If defined, it should handle all wanted feedback
                to the user.
            quitfunc_args (tuple, optional): Optional tuple of arguments to
                supply to `quitfunc`.
            key (str, optional): An optional key for naming this
                session and make it unique from other editing sessions.
            persistent (bool, optional): Make the editor survive a reboot. Note
                that if this is set, all callables must be possible to pickle
            codefunc (bool, optional): If given, will run the editor in code mode.
                This will be called as `codefunc(caller, buf)`.

        Notes:
            In persistent mode, all the input callables (savefunc etc)
            must be possible to be *pickled*, this excludes e.g.
            callables that are class methods or functions defined
            dynamically or as part of another function. In
            non-persistent mode no such restrictions exist.



        """
        self._key = key
        self._caller = caller
        self._caller.ndb._eveditor = self
        self._buffer = ""
        self._unsaved = False
        self._persistent = persistent
        self._indent = 0

        if loadfunc:
            self._loadfunc = loadfunc
        else:
            self._loadfunc = lambda caller: self._buffer
        self.load_buffer()
        if savefunc:
            self._savefunc = savefunc
        else:
            self._savefunc = lambda caller, buffer: caller.msg(_ERROR_NO_SAVEFUNC)
        if quitfunc:
            self._quitfunc = quitfunc
        else:
            self._quitfunc = lambda caller: caller.msg(_DEFAULT_NO_QUITFUNC)
        self._codefunc = codefunc

        # store the original version
        self._pristine_buffer = self._buffer
        self._sep = "-"

        # undo operation buffer
        self._undo_buffer = [self._buffer]
        self._undo_pos = 0
        self._undo_max = 20

        # copy buffer
        self._copy_buffer = []

        if persistent:
            # save in tuple {kwargs, other options}
            try:
                caller.attributes.add(
                    "_eveditor_saved",
                    (
                        dict(
                            loadfunc=loadfunc,
                            savefunc=savefunc,
                            quitfunc=quitfunc,
                            codefunc=codefunc,
                            key=key,
                            persistent=persistent,
                        ),
                        dict(_pristine_buffer=self._pristine_buffer, _sep=self._sep),
                    ),
                )
                caller.attributes.add("_eveditor_buffer_temp", (self._buffer, self._undo_buffer))
                caller.attributes.add("_eveditor_unsaved", False)
                caller.attributes.add("_eveditor_indent", 0)
            except Exception as err:
                caller.msg(_ERROR_PERSISTENT_SAVING.format(error=err))
                logger.log_trace(_TRACE_PERSISTENT_SAVING)
                persistent = False

        # Create the commands we need
        caller.cmdset.add(EvEditorCmdSet, persistent=persistent)

        # echo inserted text back to caller
        self._echo_mode = True

        # show the buffer ui
        self.display_buffer()

    def load_buffer(self):
        """
        Load the buffer using the load function hook.

        """
        try:
            self._buffer = self._loadfunc(self._caller)
            if not isinstance(self._buffer, str):
                self._caller.msg(
                    f"|rBuffer is of type |w{type(self._buffer)})|r. "
                    "Continuing, it is converted to a string "
                    "(and will be saved as such)!|n"
                )
                self._buffer = to_str(self._buffer)
        except Exception as e:
            from evennia.utils import logger

            logger.log_trace()
            self._caller.msg(_ERROR_LOADFUNC.format(error=e))

    def get_buffer(self):
        """
        Return:
            buffer (str): The current buffer.

        """
        return self._buffer

    def update_buffer(self, buf):
        """
        This should be called when the buffer has been changed
        somehow.  It will handle unsaved flag and undo updating.

        Args:
            buf (str): The text to update the buffer with.

        """
        if is_iter(buf):
            buf = "\n".join(buf)

        if buf != self._buffer:
            self._buffer = buf
            self.update_undo()
            self._unsaved = True
            if self._persistent:
                self._caller.attributes.add(
                    "_eveditor_buffer_temp", (self._buffer, self._undo_buffer)
                )
                self._caller.attributes.add("_eveditor_unsaved", True)
                self._caller.attributes.add("_eveditor_indent", self._indent)

    def quit(self):
        """
        Cleanly exit the editor.

        """
        try:
            self._quitfunc(self._caller)
        except Exception as e:
            self._caller.msg(_ERROR_QUITFUNC.format(error=e))
        self._caller.nattributes.remove("_eveditor")
        self._caller.attributes.remove("_eveditor_buffer_temp")
        self._caller.attributes.remove("_eveditor_saved")
        self._caller.attributes.remove("_eveditor_unsaved")
        self._caller.attributes.remove("_eveditor_indent")
        self._caller.cmdset.remove(EvEditorCmdSet)

    def save_buffer(self):
        """
        Saves the content of the buffer.

        """
        if self._unsaved or self._codefunc:
            # always save code - this allows us to tie execution to
            # saving if we want.
            try:
                if self._savefunc(self._caller, self._buffer):
                    # Save codes should return a true value to indicate
                    # save worked. The saving function is responsible for
                    # any status messages.
                    self._unsaved = False
            except Exception as e:
                self._caller.msg(_ERROR_SAVEFUNC.format(error=e))
        else:
            self._caller.msg(_MSG_SAVE_NO_CHANGE)

    def update_undo(self, step=None):
        """
        This updates the undo position.

        Args:
            step (int, optional): The amount of steps
                to progress the undo position to. This
                may be a negative value for undo and
                a positive value for redo.

        """
        if step and step < 0:
            # undo
            if self._undo_pos <= 0:
                self._caller.msg(_MSG_NO_UNDO)
            else:
                self._undo_pos = max(0, self._undo_pos + step)
                self._buffer = self._undo_buffer[self._undo_pos]
                self._caller.msg(_MSG_UNDO)
        elif step and step > 0:
            # redo
            if self._undo_pos >= len(self._undo_buffer) - 1 or self._undo_pos + 1 >= self._undo_max:
                self._caller.msg(_MSG_NO_REDO)
            else:
                self._undo_pos = min(
                    self._undo_pos + step, min(len(self._undo_buffer), self._undo_max) - 1
                )
                self._buffer = self._undo_buffer[self._undo_pos]
                self._caller.msg(_MSG_REDO)
        if not self._undo_buffer or (
            self._undo_buffer and self._buffer != self._undo_buffer[self._undo_pos]
        ):
            # save undo state
            self._undo_buffer = self._undo_buffer[: self._undo_pos + 1] + [self._buffer]
            self._undo_pos = len(self._undo_buffer) - 1

    def display_buffer(self, buf=None, offset=0, linenums=True, options={"raw": False}):
        """
        This displays the line editor buffer, or selected parts of it.

        Args:
            buf (str, optional): The buffer or part of buffer to display.
            offset (int, optional): If `buf` is set and is not the full buffer,
                `offset` should define the actual starting line number, to
                get the linenum display right.
            linenums (bool, optional): Show line numbers in buffer.
            options: raw (bool, optional): Tell protocol to not parse
                formatting information.

        """
        if buf is None:
            buf = self._buffer
        if is_iter(buf):
            buf = "\n".join(buf)

        lines = buf.split("\n")
        nlines = len(lines)
        nwords = len(buf.split())
        nchars = len(buf)

        sep = self._sep
        header = (
            "|n"
            + sep * 10
            + _("Line Editor [{name}]").format(name=self._key)
            + sep * (_DEFAULT_WIDTH - 24 - len(self._key))
        )
        footer = (
            "|n"
            + sep * 10
            + "[l:%02i w:%03i c:%04i]" % (nlines, nwords, nchars)
            + sep * 12
            + _("(:h for help)")
            + sep * (_DEFAULT_WIDTH - 54)
        )
        if linenums:
            main = "\n".join(
                "|b%02i|||n %s" % (iline + 1 + offset, raw(line))
                for iline, line in enumerate(lines)
            )
        else:
            main = "\n".join([raw(line) for line in lines])
        string = "%s\n%s\n%s" % (header, main, footer)
        self._caller.msg(string, options=options)

    def display_help(self):
        """
        Shows the help entry for the editor.

        """
        string = self._sep * _DEFAULT_WIDTH + _HELP_TEXT
        if self._codefunc:
            string += _HELP_CODE
        string += _HELP_LEGEND + self._sep * _DEFAULT_WIDTH
        self._caller.msg(string)

    def deduce_indent(self, line, buffer):
        """
        Try to deduce the level of indentation of the given line.

        """
        keywords = {
            "elif ": ["if "],
            "else:": ["if ", "try"],
            "except": ["try:"],
            "finally:": ["try:"],
        }
        opening_tags = ("if ", "try:", "for ", "while ")

        # If the line begins by one of the given keywords
        indent = self._indent
        if any(line.startswith(kw) for kw in keywords.keys()):
            # Get the keyword and matching begin tags
            keyword = [kw for kw in keywords if line.startswith(kw)][0]
            begin_tags = keywords[keyword]
            for oline in reversed(buffer.splitlines()):
                if any(oline.lstrip(" ").startswith(tag) for tag in begin_tags):
                    # This line begins with a begin tag, takes the identation
                    indent = (len(oline) - len(oline.lstrip(" "))) / 4
                    break

            self._indent = indent + 1
            if self._persistent:
                self._caller.attributes.add("_eveditor_indent", self._indent)
        elif any(line.startswith(kw) for kw in opening_tags):
            self._indent = indent + 1
            if self._persistent:
                self._caller.attributes.add("_eveditor_indent", self._indent)

        line = " " * 4 * indent + line
        return line

    def decrease_indent(self):
        """Decrease automatic indentation by 1 level."""
        if self._codefunc and self._indent > 0:
            self._indent -= 1
            if self._persistent:
                self._caller.attributes.add("_eveditor_indent", self._indent)

    def increase_indent(self):
        """Increase automatic indentation by 1 level."""
        if self._codefunc and self._indent >= 0:
            self._indent += 1
            if self._persistent:
                self._caller.attributes.add("_eveditor_indent", self._indent)

    def swap_autoindent(self):
        """Swap automatic indentation on or off."""
        if self._codefunc:
            if self._indent >= 0:
                self._indent = -1
            else:
                self._indent = 0

            if self._persistent:
                self._caller.attributes.add("_eveditor_indent", self._indent)
