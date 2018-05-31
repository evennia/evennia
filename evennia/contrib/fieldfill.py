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
"""

SAMPLE_FORM = [
{"fieldname":"Player", "fieldtype":"text", "max":30, "default":"Ashley"},
{"fieldname":"Delay", "fieldtype":"number", "min":3, "max":30, "default":10},
{"fieldname":"Message", "fieldtype":"text", "min":3, "max":200,
"default": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non urna ante. Etiam maximus orci ut commodo lobortis. Sed sodales sed libero quis fermentum. Nunc vel semper ante. Donec mattis nisl eget condimentum mattis. Pellentesque ac semper lorem. Sed augue."
}
]

def init_fill_field(form, caller, callback):
    """
    Presents a player with a fillable form.
    """
    
    # Pass kwargs to store data needed in the menu
    kwargs = {
    "formdata":form_template_to_dict(form_template)
    }
    
    # Initialize menu of selections
    evmenu.EvMenu(caller, "evennia.contrib.fieldfill", startnode="menunode_fieldfill", **kwargs)
    

def menunode_fieldfill(caller, raw_string, **kwargs):
    """
    Repeating node to fill a menu field
    """
    # Retrieve menu info
    formdata = caller.ndb._menutree.formdata

    
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
    formtable = evtable.EvTable(border="cells")
    field_name_width = 3
    
    for field in formtemplate:
        new_fieldname = ""
        new_fieldvalue = ""
        # Get field name
        new_fieldname = "|w" + field["fieldname"] + ":|n"
        if len(field["fieldname"]) + 5 > field_name_width:
            field_name_width = len(field["fieldname"]) + 5
        # Get field value
        new_fieldvalue = str(formdata[field["fieldname"]])
        # Add name and value to table
        formtable.add_row(new_fieldname, new_fieldvalue)
        
    formtable.reformat_column(0, align="r", width=field_name_width)
    formtable.reformat(valign="t", width=80)
        
    return formtable
    
class CmdTest(Command):
    """
    Test stuff
    """

    key = "test"

    def func(self):
        SAMPLE_FORM_DATA = form_template_to_dict(SAMPLE_FORM)
        self.caller.msg(display_formdata(SAMPLE_FORM, SAMPLE_FORM_DATA))