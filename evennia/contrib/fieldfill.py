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
"""

SAMPLE_FORM = [
{"fieldname":"Player", "fieldtype":"text", "max":30, "blankmsg":"(Name of an online player)"},
{"fieldname":"Delay", "fieldtype":"number", "min":3, "max":30, "default":10},
{"fieldname":"Message", "fieldtype":"text", "min":3, "max":200,
"default": "Lorem ipsum dolor sit amet"
}
]

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
    evmenu.EvMenu(caller, "evennia.contrib.fieldfill", startnode="menunode_fieldfill", **kwargs)
    

def menunode_fieldfill(caller, raw_string, **kwargs):
    """
    Repeating node to fill a menu field
    """
    # Retrieve menu info
    formdata = caller.ndb._menutree.formdata
    formtemplate = caller.ndb._menutree.formtemplate
    
    # Display current form data
    text = display_formdata(formtemplate, formdata)
    options = ({"key": "_default",
               "goto":"menunode_fieldfill"})
               
    if raw_string:
        if raw_string.lower().strip() == "show":
            return text, options
        elif "=" not in raw_string:
            text = None
            caller.msg("NO!")
            return text, options
        else:
            entry = raw_string.split("=", 1)
            fieldname = entry[0].strip()
            newvalue = entry[1].strip()
            caller.msg("Setting %s to %s!" % (fieldname, newvalue))
            text = None
    
    return text, options

    
def form_template_to_dict(formtemplate):
    """
    Returns dictionary of field name:value pairs from form template
    """
    formdict = {}
    
    for field in formtemplate:
        fieldvalue = ""
        if "default" in field:
            fieldvalue = field["default"]
        formdict.update({field["fieldname"]:fieldvalue})
    
    return formdict
    
def display_formdata(formtemplate, formdata):
    """
    Displays a form's current data as a table
    """
    formtable = evtable.EvTable(border="rows", valign="t", maxwidth=80)
    field_name_width = 5
    
    for field in formtemplate:
        new_fieldname = ""
        new_fieldvalue = ""
        # Get field name
        new_fieldname = "|w" + field["fieldname"] + ":|n"
        if len(field["fieldname"]) + 5 > field_name_width:
            field_name_width = len(field["fieldname"]) + 5
        # Get field value
        new_fieldvalue = str(formdata[field["fieldname"]])
        # Use blank message if field is blank and once is present
        if new_fieldvalue == "" and "blankmsg" in field:
            new_fieldvalue = "|x" + str(field["blankmsg"]) + "|n"
        # Add name and value to table
        formtable.add_row(new_fieldname, new_fieldvalue)
        
    formtable.reformat_column(0, align="r", width=field_name_width)
    formtable.reformat_column(1, pad_left=0)
        
    return formtable
    
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