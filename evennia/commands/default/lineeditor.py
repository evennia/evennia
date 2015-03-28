"""
Evennia Line Editor

This implements an advanced line editor for editing longer texts
in-game. The editor mimics the command mechanisms of the VI editor as
far as possible.

Features of the editor:
    undo/redo.
    edit/replace on any line of the buffer.
    search&replace text anywhere in buffer.
    formatting of buffer, or selection, to certain width + indentations.
    allow to echo the input or not, depending on your client.


Whereas the editor is intended to be called from other commands that
requires more elaborate text editing of data, there is also a
stand-alone editor command for editing Attributes at the end of this
module. To use it just import and add it to your default `cmdset`.
"""

import re
from django.conf import settings
from evennia import Command, CmdSet, utils
from evennia import syscmdkeys
from evennia.contrib.menusystem import prompt_yesno

CMD_NOMATCH = syscmdkeys.CMD_NOMATCH
CMD_NOINPUT = syscmdkeys.CMD_NOINPUT

RE_GROUP = re.compile(r"\".*?\"|\'.*?\'|\S*")
_DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH


class CmdEditorBase(Command):
    """
    Base parent for editor commands
    """
    locks = "cmd:all()"
    help_entry = "LineEditor"

    code = None
    editor = None

    def parse(self):
        """
        Handles pre-parsing

        Editor commands are on the form
            :cmd [li] [w] [txt]

        Where all arguments are optional.
            li  - line number (int), starting from 1. This could also
                  be a range given as <l>:<l>.
            w   - word(s) (string), could be encased in quotes.
            txt - extra text (string), could be encased in quotes.
        """

        linebuffer = []
        if self.editor:
            linebuffer = self.editor.buffer.split("\n")
        nlines = len(linebuffer)

        # The regular expression will split the line by whitespaces,
        # stripping extra whitespaces, except if the text is
        # surrounded by single- or double quotes, in which case they
        # will be kept together and extra whitespace preserved. You
        # can input quotes on the line by alternating single and
        # double quotes.
        arglist = [part for part in RE_GROUP.findall(self.args) if part]
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
        if arglist and ':' in arglist[0]:
            part1, part2 = arglist[0].split(':')
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
        lstr = ""
        if not linerange or lstart + 1 == lend:
            lstr = "line %i" % (lstart + 1)
        else:
            lstr = "lines %i-%i" % (lstart + 1, lend)

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

    def func(self):
        "Implements the Editor commands"
        pass


class CmdLineInput(CmdEditorBase):
    """
    No command match - Inputs line of text into buffer.
    """
    key = CMD_NOMATCH
    aliases = [CMD_NOINPUT]

    def func(self):
        """
        Adds the line without any formatting changes.
        """
        # add a line of text
        if not self.editor.buffer:
            buf = self.args
        else:
            buf = self.editor.buffer + "\n%s" % self.args
        self.editor.update_buffer(buf)
        if self.editor.echo_mode:
            # need to do it here or we will be off one line
            cline = len(self.editor.buffer.split('\n'))
            self.caller.msg("{b%02i|{n %s" % (cline, self.args))


class CmdEditorGroup(CmdEditorBase):
    """
    Commands for the editor
    """
    key = ":editor_command_group"
    aliases = [":","::", ":::", ":h", ":w", ":wq", ":q", ":q!", ":u", ":uu", ":UU",
               ":dd", ":dw", ":DD", ":y", ":x", ":p", ":i",
               ":r", ":I", ":A", ":s", ":S", ":f", ":fi", ":fd", ":echo"]
    arg_regex = r"\s.*?|$"

    def func(self):
        """
        This command handles all the in-editor :-style commands. Since
        each command is small and very limited, this makes for a more
        efficient presentation.
        """
        caller = self.caller
        editor = self.editor
        linebuffer = self.linebuffer
        lstart, lend = self.lstart, self.lend
        cmd = self.cmdstring
        echo_mode = self.editor.echo_mode
        string = ""

        if cmd == ":":
            # Echo buffer
            if self.linerange:
                buf = linebuffer[lstart:lend]
                string = editor.display_buffer(buf=buf, offset=lstart)
            else:
                string = editor.display_buffer()
        elif cmd == "::":
            # Echo buffer without the line numbers and syntax parsing
            if self.linerange:
                buf = linebuffer[lstart:lend]
                string = editor.display_buffer(buf=buf,
                                               offset=lstart,
                                               linenums=False)
            else:
                string = editor.display_buffer(linenums=False)
            self.caller.msg(string, raw=True)
            return
        elif cmd == ":::":
            # Insert single colon alone on a line
            editor.update_buffer(editor.buffer + "\n:")
            if echo_mode:
                string = "Single ':' added to buffer."
        elif cmd == ":h":
            # help entry
            string = editor.display_help()
        elif cmd == ":w":
            # save without quitting
            string = editor.save_buffer()
        elif cmd == ":wq":
            # save and quit
            string = editor.save_buffer()
            string += " " + editor.quit()
        elif cmd == ":q":
            # quit. If not saved, will ask
            if self.editor.unsaved:
                prompt_yesno(caller, "Save before quitting?",
                             yescode = "self.caller.ndb._lineeditor.save_buffer()\nself.caller.ndb._lineeditor.quit()",
                             nocode = "self.caller.msg(self.caller.ndb._lineeditor.quit())", default="Y")
            else:
                string = editor.quit()
        elif cmd == ":q!":
            # force quit, not checking saving
            string = editor.quit()
        elif cmd == ":u":
            # undo
            string = editor.update_undo(-1)
        elif cmd == ":uu":
            # redo
            string = editor.update_undo(1)
        elif cmd == ":UU":
            # reset buffer
            editor.update_buffer(editor.pristine_buffer)
            string = "Reverted all changes to the buffer back to original state."
        elif cmd == ":dd":
            # :dd <l> - delete line <l>
            buf = linebuffer[:lstart] + linebuffer[lend:]
            editor.update_buffer(buf)
            string = "Deleted %s." % (self.lstr)
        elif cmd == ":dw":
            # :dw <w> - delete word in entire buffer
            # :dw <l> <w> delete word only on line(s) <l>
            if not self.arg1:
                string = "You must give a search word to delete."
            else:
                if not self.linerange:
                    lstart = 0
                    lend = self.cline + 1
                    string = "Removed %s for lines %i-%i." % (self.arg1, lstart + 1, lend + 1)
                else:
                    string = "Removed %s for %s." % (self.arg1, self.lstr)
                sarea = "\n".join(linebuffer[lstart:lend])
                sarea = re.sub(r"%s" % self.arg1.strip("\'").strip('\"'), "", sarea, re.MULTILINE)
                buf = linebuffer[:lstart] + sarea.split("\n") + linebuffer[lend:]
                editor.update_buffer(buf)
        elif cmd == ":DD":
            # clear buffer
            editor.update_buffer("")
            string = "Cleared %i lines from buffer." % self.nlines
        elif cmd == ":y":
            # :y <l> - yank line(s) to copy buffer
            cbuf = linebuffer[lstart:lend]
            editor.copy_buffer = cbuf
            string = "%s, %s yanked." % (self.lstr.capitalize(), cbuf)
        elif cmd == ":x":
            # :x <l> - cut line to copy buffer
            cbuf = linebuffer[lstart:lend]
            editor.copy_buffer = cbuf
            buf = linebuffer[:lstart] + linebuffer[lend:]
            editor.update_buffer(buf)
            string = "%s, %s cut." % (self.lstr.capitalize(), cbuf)
        elif cmd == ":p":
            # :p <l> paste line(s) from copy buffer
            if not editor.copy_buffer:
                string = "Copy buffer is empty."
            else:
                buf = linebuffer[:lstart] + editor.copy_buffer + linebuffer[lstart:]
                editor.update_buffer(buf)
                string = "Copied buffer %s to %s." % (editor.copy_buffer, self.lstr)
        elif cmd == ":i":
            # :i <l> <txt> - insert new line
            new_lines = self.args.split('\n')
            if not new_lines:
                string = "You need to enter a new line and where to insert it."
            else:
                buf = linebuffer[:lstart] + new_lines + linebuffer[lstart:]
                editor.update_buffer(buf)
                string = "Inserted %i new line(s) at %s." % (len(new_lines), self.lstr)
        elif cmd == ":r":
            # :r <l> <txt> - replace lines
            new_lines = self.args.split('\n')
            if not new_lines:
                string = "You need to enter a replacement string."
            else:
                buf = linebuffer[:lstart] + new_lines + linebuffer[lend:]
                editor.update_buffer(buf)
                string = "Replaced %i line(s) at %s." % (len(new_lines), self.lstr)
        elif cmd == ":I":
            # :I <l> <txt> - insert text at beginning of line(s) <l>
            if not self.args:
                string = "You need to enter text to insert."
            else:
                buf = linebuffer[:lstart] + ["%s%s" % (self.args, line) for line in linebuffer[lstart:lend]] + linebuffer[lend:]
                editor.update_buffer(buf)
                string = "Inserted text at beginning of %s." % self.lstr
        elif cmd == ":A":
            # :A <l> <txt> - append text after end of line(s)
            if not self.args:
                string = "You need to enter text to append."
            else:
                buf = linebuffer[:lstart] + ["%s%s" % (line, self.args) for line in linebuffer[lstart:lend]] + linebuffer[lend:]
                editor.update_buffer(buf)
                string = "Appended text to end of %s." % self.lstr
        elif cmd == ":s":
            # :s <li> <w> <txt> - search and replace words
            # in entire buffer or on certain lines
            if not self.arg1 or not self.arg2:
                string = "You must give a search word and something to replace it with."
            else:
                if not self.linerange:
                    lstart = 0
                    lend = self.cline + 1
                    string = "Search-replaced %s -> %s for lines %i-%i." % (self.arg1, self.arg2, lstart + 1 , lend)
                else:
                    string = "Search-replaced %s -> %s for %s." % (self.arg1, self.arg2, self.lstr)
                sarea = "\n".join(linebuffer[lstart:lend])

                regex = r"%s|^%s(?=\s)|(?<=\s)%s(?=\s)|^%s$|(?<=\s)%s$"
                regarg = self.arg1.strip("\'").strip('\"')
                if " " in regarg:
                    regarg = regarg.replace(" ", " +")
                sarea = re.sub(regex % (regarg, regarg, regarg, regarg, regarg), self.arg2.strip("\'").strip('\"'), sarea, re.MULTILINE)
                buf = linebuffer[:lstart] + sarea.split("\n") + linebuffer[lend:]
                editor.update_buffer(buf)
        elif cmd == ":f":
            # :f <l> flood-fill buffer or <l> lines of buffer.
            width = _DEFAULT_WIDTH
            if not self.linerange:
                lstart = 0
                lend = self.cline + 1
                string = "Flood filled lines %i-%i." % (lstart + 1 , lend)
            else:
                string = "Flood filled %s." % self.lstr
            fbuf = "\n".join(linebuffer[lstart:lend])
            fbuf = utils.fill(fbuf, width=width)
            buf = linebuffer[:lstart] + fbuf.split("\n") + linebuffer[lend:]
            editor.update_buffer(buf)
        elif cmd == ":fi":
            # :fi <l> indent buffer or lines <l> of buffer.
            indent = " " * 4
            if not self.linerange:
                lstart = 0
                lend = self.cline + 1
                string = "Indented lines %i-%i." % (lstart + 1 , lend)
            else:
                string = "Indented %s." % self.lstr
            fbuf = [indent + line for line in linebuffer[lstart:lend]]
            buf = linebuffer[:lstart] + fbuf + linebuffer[lend:]
            editor.update_buffer(buf)
        elif cmd == ":fd":
            # :fi <l> indent buffer or lines <l> of buffer.
            if not self.linerange:
                lstart = 0
                lend = self.cline + 1
                string = "Removed left margin (dedented) lines %i-%i." % (lstart + 1 , lend)
            else:
                string = "Removed left margin (dedented) %s." % self.lstr
            fbuf = "\n".join(linebuffer[lstart:lend])
            fbuf = utils.dedent(fbuf)
            buf = linebuffer[:lstart] + fbuf.split("\n") + linebuffer[lend:]
            editor.update_buffer(buf)
        elif cmd == ":echo":
            # set echoing on/off
            editor.echo_mode = not editor.echo_mode
            string = "Echo mode set to %s" % editor.echo_mode
        caller.msg(string)


class EditorCmdSet(CmdSet):
    "CmdSet for the editor commands"
    key = "editorcmdset"
    mergetype = "Replace"


class LineEditor(object):
    """
    This defines a line editor object. It creates all relevant commands
    and tracks the current state of the buffer. It also cleans up after
    itself.
    """

    def __init__(self, caller,
                 loadfunc=None, loadfunc_args=None,
                 savefunc=None, savefunc_args=None,
                 quitfunc=None, quitfunc_args=None,
                 key=""):
        """
        caller - who is using the editor.

        loadfunc - this will be called as `func(*loadfunc_args)` when the
                   editor is first started, e.g. for pre-loading text into it.
        loadfunc_args - optional tuple of arguments to supply to `loadfunc`.
        savefunc - this will be called as `func(*savefunc_args)` when the
                   save-command is given and is used to actually determine
                   where/how result is saved. It should return `True` if save
                   was successful and also handle any feedback to the user.
        savefunc_args - optional tuple of arguments to supply to `savefunc`.
        quitfunc - this will optionally be called as `func(*quitfunc_args)`
                   when the editor is exited. If defined, it should handle
                   all wanted feedback to the user.
        quitfunc_args - optional tuple of arguments to supply to `quitfunc`.

        key = an optional key for naming this session (such as which attribute
              is being edited).
        """
        self.key = key
        self.caller = caller
        self.caller.ndb._lineeditor = self
        self.buffer = ""
        self.unsaved = False

        if loadfunc:
            # execute command for loading initial data
            try:
                args = loadfunc_args or ()
                self.buffer = loadfunc(*args)
            except Exception, e:
                caller.msg("%s\n{rBuffer load function error. Could not load initial data.{n" % e)
        if not savefunc:
            # If no save function is defined, save an error-reporting function
            err = "{rNo save function defined. Buffer cannot be saved.{n"
            caller.msg(err)
            savefunc = lambda: self.caller.msg(err)
        self.savefunc = savefunc
        self.savefunc_args = savefunc_args or ()
        self.quitfunc = quitfunc
        self.quitfunc_args = quitfunc_args or ()

        # Create the commands we need
        cmd1 = CmdLineInput()
        cmd1.editor = self
        cmd1.obj = self
        cmd2 = CmdEditorGroup()
        cmd2.obj = self
        cmd2.editor = self
        # Populate cmdset and add it to caller
        editor_cmdset = EditorCmdSet()
        editor_cmdset.add(cmd1)
        editor_cmdset.add(cmd2)
        self.caller.cmdset.add(editor_cmdset)

        # store the original version
        self.pristine_buffer = self.buffer
        self.sep = "-"

        # undo operation buffer
        self.undo_buffer = [self.buffer]
        self.undo_pos = 0
        self.undo_max = 20

        # copy buffer
        self.copy_buffer = []

        # echo inserted text back to caller
        self.echo_mode = False

        # show the buffer ui
        self.caller.msg(self.display_buffer())

    def update_buffer(self, buf):
        """
        This should be called when the buffer has been changed somehow.
        It will handle unsaved flag and undo updating.
        """
        if utils.is_iter(buf):
            buf = "\n".join(buf)

        if buf != self.buffer:
            self.buffer = buf
            self.update_undo()
            self.unsaved = True

    def quit(self):
        """
        Cleanly exit the editor.
        """
        if self.quitfunc:
            # call quit function hook if available
            try:
                self.quitfunc(*self.quitfunc_args)
            except Exception, e:
                self.caller.msg("%s\n{Quit function gave an error. Skipping.{n" % e)
        del self.caller.ndb._lineeditor
        self.caller.cmdset.delete(EditorCmdSet)
        if self.quitfunc:
            # if quitfunc is defined, it should manage exit messages.
            return ""
        return "Exited editor."

    def save_buffer(self):
        """
        Saves the content of the buffer. The 'quitting' argument is a bool
        indicating whether or not the editor intends to exit after saving.
        """
        if self.unsaved:
            try:
                if self.savefunc(*self.savefunc_args):
                    # Save codes should return a true value to indicate
                    # save worked. The saving function is responsible for
                    # any status messages.
                    self.unsaved = False
                return ""
            except Exception, e:
                return "%s\n{rSave function gave an error. Buffer not saved." % e
        else:
            return "No changes need saving."

    def update_undo(self, step=None):
        """
        This updates the undo position.

        """
        if step and step < 0:
            if self.undo_pos <= 0:
                return "Nothing to undo."
            self.undo_pos = max(0, self.undo_pos + step)
            self.buffer = self.undo_buffer[self.undo_pos]
            return "Undo."
        elif step and step > 0:
            if self.undo_pos >= len(self.undo_buffer) - 1 or self.undo_pos + 1 >= self.undo_max:
                return "Nothing to redo."
            self.undo_pos = min(self.undo_pos + step, min(len(self.undo_buffer), self.undo_max) - 1)
            self.buffer = self.undo_buffer[self.undo_pos]
            return "Redo."
        if not self.undo_buffer or (self.undo_buffer and self.buffer != self.undo_buffer[self.undo_pos]):
            self.undo_buffer = self.undo_buffer[:self.undo_pos + 1] + [self.buffer]
            self.undo_pos = len(self.undo_buffer) - 1

    def display_buffer(self, buf=None, offset=0, linenums=True):
        """
        This displays the line editor buffer, or selected parts of it.

        If `buf` is set and is not the full buffer, `offset` should define
        the starting line number, to get the linenum display right.
        """
        if buf == None:
            buf = self.buffer
        if utils.is_iter(buf):
            buf = "\n".join(buf)

        lines = buf.split('\n')
        nlines = len(lines)
        nwords = len(buf.split())
        nchars = len(buf)

        sep = self.sep
        header = "{n" + sep * 10 + "Line Editor [%s]" % self.key + sep * (_DEFAULT_WIDTH-25-len(self.key))
        footer = "{n" + sep * 10 + "[l:%02i w:%03i c:%04i]" % (nlines, nwords, nchars) + sep * 12 + "(:h for help)" + sep * 23
        if linenums:
            main = "\n".join("{b%02i|{n %s" % (iline + 1 + offset, line) for iline, line in enumerate(lines))
        else:
            main = "\n".join(lines)
        string = "%s\n%s\n%s" % (header, main, footer)
        return string

    def display_help(self):
        """
        Shows the help entry for the editor.
        """
        string = self.sep * _DEFAULT_WIDTH + """
<txt>  - any non-command is appended to the end of the buffer.
:  <l> - view buffer or only line <l>
:: <l> - view buffer without line numbers or other parsing
:::    - print a ':' as the only character on the line...
:h     - this help.

:w     - saves the buffer (don't quit)
:wq    - save buffer and quit
:q     - quits (will be asked to save if buffer was changed)
:q!    - quit without saving, no questions asked

:u     - (undo) step backwards in undo history
:uu    - (redo) step forward in undo history
:UU    - reset all changes back to initial

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
""" + self.sep * _DEFAULT_WIDTH
        return string


#
# Editor access command for editing a given attribute on an object.
#

class CmdEditor(Command):
    """
    Start editor

    Usage:
        @editor <obj>/<attr>

    This will start Evennia's powerful line editor to edit an
    Attribute. The editor has a host of commands on its own. Use :h
    for a list of commands.

    """

    key = "@editor"
    aliases = ["@edit"]
    locks = "cmd:perm(editor) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "setup and start the editor"

        if not self.args or not '/' in self.args:
            self.caller.msg("Usage: @editor <obj>/<attrname>")
            return
        self.objname, self.attrname = [part.strip()
                                            for part in self.args.split("/", 1)]
        self.obj = self.caller.search(self.objname)
        if not self.obj:
            return

        # hook save/load functions
        def load_attr():
            "inital loading of buffer data from given attribute."
            target = self.obj.attributes.get(self.attrname)
            if target is not None and not isinstance(target, basestring):
                typ = type(target).__name__
                self.caller.msg("{RWARNING! Saving this buffer will overwrite the current attribute (of type %s) with a string!{n" % typ)
            return target and str(target) or ""

        def save_attr():
            """
            Save line buffer to given attribute name. This should
            return True if successful and also report its status.
            """
            self.obj.attributes.add(self.attrname, self.editor.buffer)
            self.caller.msg("Saved.")
            return True

        def quit_hook():
            "Example quit hook. Since it's given, it's responsible for giving feedback messages."
            self.caller.msg("Exited Editor.")

        editor_key = "%s/%s" % (self.objname, self.attrname)
        # start editor, it will handle things from here.
        self.editor = utils.get_line_editor()(
            self.caller,
            loadfunc=load_attr,
            savefunc=save_attr,
            quitfunc=quit_hook,
            key=editor_key
        )
