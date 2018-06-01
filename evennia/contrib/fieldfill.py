"""
Fyield Fyill
"""

from evennia.utils import evmenu, evtable
from evennia import Command

"""
Complete field data is sent to the given callable as a dictionary (field:value pairs)

FORM LIST/DICTIONARY VALUES:
Required:
    fieldname - Name of the field as presented to the player
    fieldtype - Type of field, either 'text' or 'number'

Optional:
    max - Maximum character length (if text) or value (if number)
    min - Minimum charater length (if text) or value (if number)
    default - Initial value (blank if not given)
    blankmsg - Message to show when field is blank
    verifyfunc - Name of a callable used to verify input
    preformtxt - Text to put before the whole form table. Can be put in any field.
    postformtxt - Text to put after the whole form table. Can be put in any field.
"""

SAMPLE_FORM = [
{"fieldname":"Player", "fieldtype":"text", "max":30, "blankmsg":"(Name of an online player)",
 "preformtxt":"Send a delayed message to another player:", "postformtxt":"Syntax: <field> = <new value>|/Or: clear <field>, help, show, quit"},
{"fieldname":"Delay", "fieldtype":"number", "min":3, "max":30, "default":10},
{"fieldname":"Message", "fieldtype":"text", "min":3, "max":200, "blankmsg":"(Message up to 200 characters)"}
]

class FieldEvMenu(evmenu.EvMenu):
    """
    Custom EvMenu type with its own node formatter - removes extraneous lines
    """
    
    def node_formatter(self, nodetext, optionstext):
        """
        Formats the entirety of the node.

        Args:
            nodetext (str): The node text as returned by `self.nodetext_formatter`.
            optionstext (str): The options display as returned by `self.options_formatter`.
            caller (Object, Account or None, optional): The caller of the node.

        Returns:
            node (str): The formatted node to display.

        """
        # Only return node text, no options or separators
        return nodetext
    

def init_fill_field(formtemplate, caller, callback):
    """
    Presents a player with a fillable form.
    """
    # Initialize form data from the template
    blank_formdata = form_template_to_dict(formtemplate)
    
    # Pass kwargs to store data needed in the menu
    kwargs = {
    "formdata":blank_formdata,
    "formtemplate": formtemplate
    }
    
    # Initialize menu of selections
    FieldEvMenu(caller, "evennia.contrib.fieldfill", startnode="menunode_fieldfill", **kwargs)
    

def menunode_fieldfill(caller, raw_string, **kwargs):
    """
    Repeating node to fill a menu field
    """
    # Syntax error goes here
    syntax_err = "Syntax: <field> = <new value>|/Or: clear <field>, help, show, quit"
    
    # Retrieve menu info
    formdata = caller.ndb._menutree.formdata
    formtemplate = caller.ndb._menutree.formtemplate
    
    # Display current form data
    text = display_formdata(formtemplate, formdata)
    options = ({"key": "_default",
               "goto":"menunode_fieldfill"})
               
    if raw_string:
        # Test for 'show' command
        if raw_string.lower().strip() == "show":
            return text, options
        # Test for 'clear' command
        cleartest = raw_string.lower().strip().split(" ", 1)
        if cleartest[0].lower() == "clear":
            text = None
            if len(cleartest) < 2:
                caller.msg(syntax_err)
                return text, options
            matched_field = None
            
            for key in formdata.keys():
                if cleartest[1].lower() in key.lower():
                    matched_field = key
                    
            if not matched_field:
                caller.msg("Field '%s' does not exist!" % cleartest[1])
                text = None
                return text, options
                
            formdata.update({matched_field:None})
            caller.ndb._menutree.formdata = formdata
            caller.msg("Field '%s' cleared." % matched_field)
            return text, options
            
        if "=" not in raw_string:
            text = None
            caller.msg(syntax_err)
            return text, options

        # Extract field name and new field value
        entry = raw_string.split("=", 1)
        fieldname = entry[0].strip()
        newvalue = entry[1].strip()
        
        # Syntax error of field name is too short or blank
        if len(fieldname) < 3:
            caller.msg(syntax_err)
            text = None
            return text, options
        
        # Attempt to match field name to field in form data
        matched_field = None
        for key in formdata.keys():
            if fieldname.lower() in key.lower():
                matched_field = key
        
        # No matched field
        if matched_field == None:
            caller.msg("Field '%s' does not exist!" % fieldname)
            text = None
            return text, options
            
        # Set new field value if match
        # Get data from template
        fieldtype = None
        max_value = None
        min_value = None
        for field in formtemplate:
            if field["fieldname"] == matched_field:
                fieldtype = field["fieldtype"]
                if "max" in field.keys():
                    max_value = field["max"]
                if "min" in field.keys():
                    min_value = field["min"]
            
        # Field type text update
        if fieldtype == "text":
            # Test for max/min
            if max_value != None:
                if len(newvalue) > max_value:
                    caller.msg("Field '%s' has a maximum length of %i characters." % (matched_field, max_value))
                    text = None
                    return text, options
            if min_value != None:
                if len(newvalue) < min_value:
                    caller.msg("Field '%s' reqiures a minimum length of %i characters." % (matched_field, min_value))
                    text = None
                    return text, options
            # Update form data
            formdata.update({matched_field:newvalue})
            caller.ndb._menutree.formdata = formdata
            caller.msg("Field '%s' set to: %s" % (matched_field, newvalue))
            text = None
                
        # Field type number update
        if fieldtype == "number":
            try:
                newvalue = int(newvalue)
            except:
                caller.msg("Field '%s' requires a number." % matched_field)
                text = None
                return text, options
            formdata.update({matched_field:newvalue})
            caller.ndb._menutree.formdata = formdata
            caller.msg("Field '%s' set to: %i" % (matched_field, newvalue))
            text = None
    
    return text, options

    
def form_template_to_dict(formtemplate):
    """
    Returns dictionary of field name:value pairs from form template
    """
    formdict = {}
    
    for field in formtemplate:
        fieldvalue = None
        if "default" in field:
            fieldvalue = field["default"]
        formdict.update({field["fieldname"]:fieldvalue})
    
    return formdict
    
def display_formdata(formtemplate, formdata):
    """
    Displays a form's current data as a table
    """
    formtable = evtable.EvTable(border="cells", valign="t", maxwidth=80)
    field_name_width = 5
    
    for field in formtemplate:
        new_fieldname = None
        new_fieldvalue = None
        # Get field name
        new_fieldname = "|w" + field["fieldname"] + ":|n"
        if len(field["fieldname"]) + 5 > field_name_width:
            field_name_width = len(field["fieldname"]) + 5
        # Get field value
        if formdata[field["fieldname"]] != None:
            new_fieldvalue = str(formdata[field["fieldname"]])
        # Use blank message if field is blank and once is present
        if new_fieldvalue == None and "blankmsg" in field:
            new_fieldvalue = "|x" + str(field["blankmsg"]) + "|n"
        elif new_fieldvalue == None:
            new_fieldvalue = " "
        # Add name and value to table
        formtable.add_row(new_fieldname, new_fieldvalue)
        
    formtable.reformat_column(0, align="r", width=field_name_width)
    # formtable.reformat_column(1, pad_left=0)
    
    # Get pre-text and/or post-text
    pretext = ""
    posttext = ""
    for field in formtemplate:
        if "preformtxt" in field:
            pretext = field["preformtxt"] + "|/"
        if "postformtxt" in field:
            posttext = "|/" + field["postformtxt"]
        
    return pretext + str(formtable) + posttext
    
class CmdTest(Command):
    """
    Test stuff
    """

    key = "test"

    def func(self):
        SAMPLE_FORM_DATA = form_template_to_dict(SAMPLE_FORM)
        self.caller.msg(display_formdata(SAMPLE_FORM, SAMPLE_FORM_DATA))
        
class CmdTestMenu(Command):
    """
    Test stuff
    """

    key = "testmenu"

    def func(self):
        init_fill_field(SAMPLE_FORM, self.caller, Placeholder)
        
def Placeholder():
    return