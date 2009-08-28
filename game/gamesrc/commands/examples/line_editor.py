"""
This is an example in-game line editor. It uses the state system of Evennia (see
gamesrc/examples/state_example.py).

Usage:
  @edit object=attributename

The editor is invoked on an object's  attribute and allows some more editing
facilities over just writing everything in one go. Check the help for more info.

If you choose to edit atribute-lists instead of simple strings, the editor adapts
by switching to line-mode.
"""

from src.cmdtable import GLOBAL_CMD_TABLE
from src.statetable import GLOBAL_STATE_TABLE
from src.objects.models import Object, Attribute
import src.defines_global

STATENAME = 'line_editor'

#editor variables and settings

BUF = '_EDITOR_EDITORBUF'
LINEMODE = '_EDITOR_LINEMODE'
NOUPDATE = '_EDITOR_NOUPDATE'
EDIT_ATTR = '_EDITOR_EDIT_ATTR'

def cmd_edit(command):
    """
    Edit an attribute using the editor.

    Usage:
      @edit[/switches] [object=]attribute

    switches:
      clear - if the attribute already had a value, clear it before
              entering the editor.
      line  - work and save in line mode
      noup  - only updates the buffer when explicitly
              listing it (avoid large screen-redraws if there's
              a lot of text)
      
    If no object is given, attribute is assumed to be defined on the
    caller.

    The editor supports modifying, replacing and inserting text into an attribute
    in various ways, as well as cancelling your changes. 

    Technically, the 'line' mode of the editor works and saves lines in a list-attribute.
    This mode supports more formatting operations than just working on a string. When
    working on a normal string (string mode) the editor has no concept of lines,
    but new text is added and inserted into the string.
    
    See the help text in the editor for more information.
    """

    source_object = command.source_object
    args = command.command_argument
    switches = command.command_switches

    if not args:
        source_object.emit_to("You must specify an attribute to @edit.")
        return
    args = args.strip()
    if '=' not in args:
        args = "me=" + args

    objname, attr = args.split('=',1)
    obj = validate_obj(source_object, objname, attr)
    if not obj:
        return    

    source_object.set_attribute(LINEMODE, 'line' in switches)
    if not 'clear' in switches:
        curr_value = obj.get_attribute_value(attr.strip())
        if type(curr_value) == type(list()):
            source_object.set_attribute(LINEMODE,True)        
        source_object.set_attribute(BUF, curr_value)
    source_object.set_attribute(NOUPDATE, 'noup' in switches)    
    
    #setup the editor temporary attributes
    source_object.set_attribute(EDIT_ATTR,args) 
    
    #enter edit state
    source_object.set_state(STATENAME)
    source_object.execute_cmd('list')

def cmd_list(command):
    """
    list the buffer
    """
    source_object = command.source_object

    buf = source_object.get_attribute_value(BUF)

    linemode = source_object.get_attribute_value(LINEMODE)

    header = "%s-----------------------------------------%s\n\r" % ('%cy', '%cn')
    attr = source_object.get_attribute_value(EDIT_ATTR)
    if linemode:
        footer = "\n\r%s@edit mode (line) (%s%s%s) (h for help)" % ('%cy','%ch',attr,'%cn%cy')    
    else:
        footer = "\n\r%s@edit mode (str) (%s%s%s) (h for help)" % ('%cy','%ch',attr,'%cn%cy')    
    if buf:        
        if type(buf)==type(list()):
            s = ""
            for i, line in enumerate(buf):
                s += "%s%2i|%s %s\n\r" % ('%ch%cw', i+1, '%cn', line)
            s = header + s[:-2] + footer    
        else:
            if linemode:
                s = "%s%2i|%s %s\n\r" % ('%ch%cw', 1, '%cn', buf)
                s = header + s + footer
            else:
                s = header + buf + footer
    else:
        s = header + footer
    source_object.emit_to(s)

def cmd_append(command):
    """
    Append text to buffer.
    """
    source_object = command.source_object    
    args = command.command_argument

    buf = source_object.get_attribute_value(BUF)

    if not args:
        args = " "

    if source_object.get_attribute_value(LINEMODE):                    
        if not buf:
            buf = [args]
        else:
            if type(buf) != type(list()):            
                buf = [buf]
            buf.extend([args])
    else:            
        if not buf:
            buf = ""
        elif buf[-1] in '.,;:':
            buf += ' '                    
        buf += args
    source_object.set_attribute(BUF, buf)

    if not source_object.get_attribute_value(NOUPDATE):
        cmd_list(command)

def cmd_insert(command):
    """
    Insert new line before given line
    """    
    source_object = command.source_object    
    args = command.command_argument
    buf = source_object.get_attribute_value(BUF)

    if source_object.get_attribute_value(LINEMODE):
        if args:
            args = args.split(" ",1)
            if len(args)>1:
                linenum, text = args[0],args[1]
            else:
                source_object.emit_to("Usage: .i # <text>")
                return 
            try:            
                buf.insert(int(linenum)-1, text)
            except:
                source_object.emit_to("%s'%s' is not a valid line number." % ('%cr',linenum))
                return
        source_object.set_attribute(BUF, buf)

        if not source_object.get_attribute_value(NOUPDATE):
            cmd_list(command)
    else:
        source_object.emit_to("%s.i only works in line mode" % '%cr')

def cmd_clear(command):
    """
    clears the buffer
    """
    source_object = command.source_object
    args = command.command_argument    
    buf = source_object.get_attribute_value(BUF)

    if source_object.get_attribute_value(LINEMODE):
        if args:
            try:
                del buf[int(args)-1]
                source_object.set_attribute(BUF,buf)
            except:
                source_object.emit_to("%sCould not clear line '%s'" % ('%cr',args))   
        else:
            source_object.set_attribute(BUF,[])
    else:        
        source_object.set_attribute(BUF,"")

    if not source_object.get_attribute_value(NOUPDATE):
        cmd_list(command)

def cmd_replace(command):
    """
    replace all occurences of a text.
    """
    source_object = command.source_object
    buf = source_object.get_attribute_value(BUF)
    if not buf:
        return
    args = command.command_argument
    if not args:
        source_object.emit_to("Usage: .r old or .r old=new")
        return

    if source_object.get_attribute_value(LINEMODE):
        if args[0].isdigit():
            num, args = args.split(" ",1)            
            if '=' in args:
                old, new = args.split('=')
                old, new = old, new
            else:
                old = args
                new = ""
            try:                
                buf[int(num)-1] = buf[int(num)-1].replace(old, new)
            except:
                source_object.emit_to("%s%s is not a valid line number." % ('%cr',num))
                return
        else:
            if '=' in args:
                old, new = args.split('=')
                old, new = old, new
            else:
                old = args
                new = ""
            newbuf = []
            for line in buf:
                newbuf.append(line.replace(old,new))
            buf = newbuf
    else: 
        if '=' in args:
            old, new = args.split('=')
            old, new = old, new
        else:
            old = args
            new = ""        
        buf = buf.replace(old, new)

    source_object.set_attribute(BUF, buf)

    if not source_object.get_attribute_value(NOUPDATE):
        cmd_list(command)
            
def cmd_save(command):
    source_object = command.source_object

    buf = source_object.get_attribute_value(BUF)
    if not buf: buf = ""

    attr = source_object.get_attribute_value(EDIT_ATTR)
    objname, attr = attr.split('=',1)

    obj = validate_obj(source_object, objname, attr)
    if not obj:
        cmd_exit(command)
    else:
        obj.set_attribute(attr, buf)        
        source_object.emit_to("%s%s=%s saved." % ('%cg',objname,attr))

def cmd_save_exit(command):        
    cmd_save(command)
    util_exit(command)

def cmd_exit(command):
    "exits without saving."
    source_object = command.source_object
    attr = source_object.get_attribute_value(EDIT_ATTR)
    source_object.emit_to('%s%s not saved/changed.' % ('%cr', attr))
    util_exit(command)

def util_exit(command):
    "cleans up and exits"
    source_object = command.source_object
    source_object.clear_attribute(BUF)
    source_object.clear_attribute(LINEMODE)
    source_object.clear_attribute(NOUPDATE)    
    source_object.clear_attribute(EDIT_ATTR)    

    source_object.clear_state()
    source_object.execute_cmd('look')
    
def cmd_help(command):
    """
    A custom help screen.
    """
    source_object = command.source_object
    buf = source_object.get_attribute_value(BUF)

    if source_object.get_attribute_value(LINEMODE):
        s = \
    """
    %sEditor commands:
      . <text>         - enter text into the buffer
      .i # <text>      - insert new line before line # 
      .c               - clear buffer
      .c #             - clear line #     
      .r <words>       - remove all matching <words>
      .r <old>=<new>   - replace all <old> with <new>
      .r # <new>       - replace line # with <new>
      .r # <old>=<new> - replace <old> with <new> on line #
      .s               - save buffer
      .xs, .sx         - save and exit
      .x, .q           - exit without saving
      .l, l, list      - list buffer         
      .h, h, help      - this help
    """
    else:
        s = \
    """
    %sEditor commands:
      . <text>         - enter text into the buffer
      .c               - clear buffer
      .r <words>       - remove all matching <words>
      .r <old>=<new>   - replace all <old> with <new>
      .s               - save buffer
      .xs, .sx         - save and exit
      .x, .q           - exit without saving
      .l, l, list      - list buffer         
      .h, h, help      - this help
    """    
    source_object.emit_to(s % '%cy')

#
# Helper function
#
def validate_obj(source_object, objname, attr):
    "Helper function"
    #test that object exists. 
    results = Object.objects.local_and_global_search(source_object, objname)
    
    if not results:
        source_object.emit_to("No name matches found for %s." % (objname,))
        return None
    if len(results) > 1:
        source_object.emit_to("Multiple name matches for: %s" % (objname,))
        s = ""
        for result in results:
            s += " %s\n\r" % (result.get_name(fullname=False),)
        s += "%d matches returned." % (len(results),)
        source_object.emit_to(s)
        return None 
    obj = results[0]
    
    #permission checks
    if not source_object.controls_other(obj):
        source_object.emit_to(defines_global.NOCONTROL_MSG)
        return None
    if not Attribute.objects.is_modifiable_attrib(attr):
        source_object.emit_to("You can't modify that attribute.")
        return None

    return obj

    
#editor entry command
GLOBAL_CMD_TABLE.add_command("@edit", cmd_edit, auto_help=True)

#create the state
GLOBAL_STATE_TABLE.add_state(STATENAME)

#editor commands
GLOBAL_STATE_TABLE.add_command(STATENAME, ".", cmd_append)
GLOBAL_STATE_TABLE.add_command(STATENAME, ".i", cmd_insert)
GLOBAL_STATE_TABLE.add_command(STATENAME, ".r", cmd_replace)
GLOBAL_STATE_TABLE.add_command(STATENAME, ".c", cmd_clear)
GLOBAL_STATE_TABLE.add_command(STATENAME, ".s", cmd_save)
GLOBAL_STATE_TABLE.add_command(STATENAME, ".xs", cmd_save_exit)
GLOBAL_STATE_TABLE.add_command(STATENAME, ".sx", cmd_save_exit)
GLOBAL_STATE_TABLE.add_command(STATENAME, ".x", cmd_exit)
GLOBAL_STATE_TABLE.add_command(STATENAME, ".q", cmd_exit)
GLOBAL_STATE_TABLE.add_command(STATENAME, ".l", cmd_list)
GLOBAL_STATE_TABLE.add_command(STATENAME, "l", cmd_list)
GLOBAL_STATE_TABLE.add_command(STATENAME, "list", cmd_list)
GLOBAL_STATE_TABLE.add_command(STATENAME, ".h", cmd_help)
GLOBAL_STATE_TABLE.add_command(STATENAME, "h", cmd_help)
GLOBAL_STATE_TABLE.add_command(STATENAME, "help", cmd_help)



