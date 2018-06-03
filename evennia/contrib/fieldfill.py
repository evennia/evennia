"""
Fyield Fyill
"""

from evennia.utils import evmenu, evtable, delay, list_to_string
from evennia import Command
from evennia.server.sessionhandler import SESSIONS

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
    cantclear - Field can't be cleared if True
    required - If True, form cannot be submitted while field is blank
    verifyfunc - Name of a callable used to verify input
"""


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
    

def init_fill_field(formtemplate, caller, callback, pretext="", posttext="", submitcmd="submit", borderstyle="cells"):
    """
    Presents a player with a fillable form.
    """
    # Initialize form data from the template
    blank_formdata = form_template_to_dict(formtemplate)
    
    # Pass kwargs to store data needed in the menu
    kwargs = {
    "formdata":blank_formdata,
    "formtemplate": formtemplate,
    "callback": callback,
    "pretext": pretext,
    "posttext": posttext,
    "submitcmd": submitcmd,
    "borderstyle": borderstyle
    }
    
    # Initialize menu of selections
    FieldEvMenu(caller, "evennia.contrib.fieldfill", startnode="menunode_fieldfill", **kwargs)
    

def menunode_fieldfill(caller, raw_string, **kwargs):
    """
    Repeating node to fill a menu field
    """
    
    # Retrieve menu info
    formdata = caller.ndb._menutree.formdata
    formtemplate = caller.ndb._menutree.formtemplate
    callback = caller.ndb._menutree.callback
    pretext = caller.ndb._menutree.pretext
    posttext = caller.ndb._menutree.posttext
    submitcmd = caller.ndb._menutree.submitcmd
    borderstyle = caller.ndb._menutree.borderstyle
    
    # Syntax error
    syntax_err = "Syntax: <field> = <new value>|/Or: clear <field>, help, show, quit|/'%s' to submit form" % submitcmd
    
    # Set help text, including listing the 'submit' command
    help_text = """Available commands:
|w<field> = <new value>:|n Set given field to new value, replacing the old value
|wclear <field>:|n Clear the value in the given field, making it blank
|wshow|n: Show the form's current values
|whelp|n: Display this help screen
|wquit|n: Quit the form menu without submitting
|w%s|n: Submit this form and quit the menu""" % submitcmd
    
    # Display current form data
    text = (display_formdata(formtemplate, formdata, pretext=pretext,
            posttext=posttext, borderstyle=borderstyle), help_text)
    options = ({"key": "_default",
               "goto":"menunode_fieldfill"})
               
    if raw_string:
        # Test for given 'submit' command
        if raw_string.lower().strip() == submitcmd:
            # Test to see if any blank fields are required
            blank_and_required = []
            for field in formtemplate:
                if "required" in field.keys():
                    # If field is required but current form data for field is blank
                    if field["required"] == True and formdata[field["fieldname"]] == None:
                        # Add to blank and required fields
                        blank_and_required.append(field["fieldname"])
            if len(blank_and_required) > 0:
                caller.msg("The following blank fields require a value: %s" % list_to_string(blank_and_required))
                text = (None, help_text)
                return text, options
            
            # If everything checks out, pass form data to the callback and end the menu!
            callback(caller, formdata)
            return None, None
        
        # Test for 'show' command
        if raw_string.lower().strip() == "show":
            return text, options
        
        # Test for 'clear' command
        cleartest = raw_string.lower().strip().split(" ", 1)
        if cleartest[0].lower() == "clear":
            text = (None, help_text)
            if len(cleartest) < 2:
                caller.msg(syntax_err)
                return text, options
            matched_field = None
            
            for key in formdata.keys():
                if cleartest[1].lower() in key.lower():
                    matched_field = key
                    
            if not matched_field:
                caller.msg("Field '%s' does not exist!" % cleartest[1])
                text = (None, help_text)
                return text, options
            
            # Test to see if field can be cleared
            for field in formtemplate:
                if field["fieldname"] == matched_field and "cantclear" in field.keys():
                    if field["cantclear"] == True:
                        caller.msg("Field '%s' can't be cleared!" % matched_field)
                        text = (None, help_text)
                        return text, options
                    
            
            # Clear the field
            formdata.update({matched_field:None})
            caller.ndb._menutree.formdata = formdata
            caller.msg("Field '%s' cleared." % matched_field)
            return text, options
            
        if "=" not in raw_string:
            text = (None, help_text)
            caller.msg(syntax_err)
            return text, options

        # Extract field name and new field value
        entry = raw_string.split("=", 1)
        fieldname = entry[0].strip()
        newvalue = entry[1].strip()
        
        # Syntax error of field name is too short or blank
        if len(fieldname) < 3:
            caller.msg(syntax_err)
            text = (None, help_text)
            return text, options
        
        # Attempt to match field name to field in form data
        matched_field = None
        for key in formdata.keys():
            if fieldname.lower() in key.lower():
                matched_field = key
        
        # No matched field
        if matched_field == None:
            caller.msg("Field '%s' does not exist!" % fieldname)
            text = (None, help_text)
            return text, options
            
        # Set new field value if match
        # Get data from template
        fieldtype = None
        max_value = None
        min_value = None
        verifyfunc = None
        for field in formtemplate:
            if field["fieldname"] == matched_field:
                fieldtype = field["fieldtype"]
                if "max" in field.keys():
                    max_value = field["max"]
                if "min" in field.keys():
                    min_value = field["min"]
                if "verifyfunc" in field.keys():
                    verifyfunc = field["verifyfunc"]
                    
            
        # Field type text update
        if fieldtype == "text":
            # Test for max/min
            if max_value != None:
                if len(newvalue) > max_value:
                    caller.msg("Field '%s' has a maximum length of %i characters." % (matched_field, max_value))
                    text = (None, help_text)
                    return text, options
            if min_value != None:
                if len(newvalue) < min_value:
                    caller.msg("Field '%s' reqiures a minimum length of %i characters." % (matched_field, min_value))
                    text = (None, help_text)
                    return text, options
                
        # Field type number update
        if fieldtype == "number":
            try:
                newvalue = int(newvalue)
            except:
                caller.msg("Field '%s' requires a number." % matched_field)
                text = (None, help_text)
                return text, options
                
        # Call verify function if present
        if verifyfunc:
            if verifyfunc(caller, newvalue) == False:
                text = (None, help_text)
                return text, options
            elif verifyfunc(caller, newvalue) != True:
                newvalue = verifyfunc(caller, newvalue)
        
        # If everything checks out, update form!!
        formdata.update({matched_field:newvalue})
        caller.ndb._menutree.formdata = formdata
        caller.msg("Field '%s' set to: %s" % (matched_field, str(newvalue)))
        text = (None, help_text)
    
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
    
def display_formdata(formtemplate, formdata,
                     pretext="", posttext="", borderstyle="cells"):
    """
    Displays a form's current data as a table
    """
    
    formtable = evtable.EvTable(border=borderstyle, valign="t", maxwidth=80)
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
        
    return pretext + "|/" + str(formtable) + "|/" + posttext
    
    
    
    
# PLACEHOLDER / EXAMPLE STUFF STARTS HEEEERE
    
def verify_online_player(caller, value):
    # Get a list of sessions
    session_list = SESSIONS.get_sessions()
    char_list = []
    matched_character = None
    
    # Get a list of online characters
    for session in session_list:
        if not session.logged_in:
            # Skip over logged out characters
            continue
        # Append to our list of online characters otherwise
        char_list.append(session.get_puppet())

    # Match player input to a character name
    for character in char_list:
        if value.lower() == character.key.lower():
            matched_character = character
    
    # If input didn't match to a character
    if not matched_character:
        # Send the player an error message unique to this function
        caller.msg("No character matching '%s' is online." % value)
        # Returning False indicates the new value is not valid
        return False
    
    # Returning anything besides True or False will replace the player's input with the returned value
    # In this case, the value becomes a reference to the character object
    # You can store data besides strings and integers in the 'formdata' dictionary this way!
    return matched_character

SAMPLE_FORM = [
{"fieldname":"Character", "fieldtype":"text", "max":30, "blankmsg":"(Name of an online player)",
 "required":True, "verifyfunc":verify_online_player},
{"fieldname":"Delay", "fieldtype":"number", "min":3, "max":30, "default":10, "cantclear":True},
{"fieldname":"Message", "fieldtype":"text", "min":3, "max":200, "blankmsg":"(Message up to 200 characters)"}
]

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
    
        pretext = "|cSend a delayed message to another player ---------------------------------------|n"
        posttext = ("|c--------------------------------------------------------------------------------|n|/"
                   "Syntax: type |c<field> = <new value>|n to change the values of the form. Given|/"
                   "player must be currently logged in, delay is given in seconds. When you are|/"
                   "finished, type '|csend|n' to send the message.|/")

        init_fill_field(SAMPLE_FORM, self.caller, init_delayed_message,
                        pretext=pretext, posttext=posttext,
                        submitcmd="send", borderstyle="none")

def sendmessage(obj, text):
    obj.msg(text)        

def init_delayed_message(caller, formdata):
    player_to_message = formdata["Character"]
    message_delay = formdata["Delay"]
    message = ("Message from %s: " % caller) + formdata["Message"]
    
    caller.msg("Message sent to %s!" % player_to_message)
    deferred = delay(message_delay, sendmessage, player_to_message, message)
    
    return
    
