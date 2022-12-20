"""
Easy fillable form

Contrib - Tim Ashley Jenkins 2018

This module contains a function that calls an easily customizable EvMenu - this
menu presents the player with a fillable form, with fields that can be filled
out in any order. Each field's value can be verified, with the function
allowing easy checks for text and integer input, minimum and maximum values /
character lengths, or can even be verified by a custom function. Once the form
is submitted, the form's data is submitted as a dictionary to any callable of
your choice.

The function that initializes the fillable form menu is fairly simple, and
includes the caller, the template for the form, and the callback(caller, result)
to which the form data will be sent to upon submission.

    init_fill_field(formtemplate, caller, formcallback)

Form templates are defined as a list of dictionaries - each dictionary
represents a field in the form, and contains the data for the field's name and
behavior. For example, this basic form template will allow a player to fill out
a brief character profile:

    PROFILE_TEMPLATE = [
    {"fieldname":"Name", "fieldtype":"text"},
    {"fieldname":"Age", "fieldtype":"number"},
    {"fieldname":"History", "fieldtype":"text"},
    ]

This will present the player with an EvMenu showing this basic form:

      Name:
       Age:
   History:

While in this menu, the player can assign a new value to any field with the
syntax <field> = <new value>, like so:

    > name = Ashley
    Field 'Name' set to: Ashley

Typing 'look' by itself will show the form and its current values.

    > look

      Name: Ashley
       Age:
   History:

Number fields require an integer input, and will reject any text that can't
be converted into an integer.

    > age = youthful
    Field 'Age' requires a number.
    > age = 31
    Field 'Age' set to: 31

Form data is presented as an EvTable, so text of any length will wrap cleanly.

    > history = EVERY MORNING I WAKE UP AND OPEN PALM SLAM[...]
    Field 'History' set to: EVERY MORNING I WAKE UP AND[...]
    > look

      Name: Ashley
       Age: 31
   History: EVERY MORNING I WAKE UP AND OPEN PALM SLAM A VHS INTO THE SLOT.
            IT'S CHRONICLES OF RIDDICK AND RIGHT THEN AND THERE I START DOING
            THE MOVES ALONGSIDE WITH THE MAIN CHARACTER, RIDDICK. I DO EVERY
            MOVE AND I DO EVERY MOVE HARD.

When the player types 'submit' (or your specified submit command), the menu
quits and the form's data is passed to your specified function as a dictionary,
like so:

    formdata = {"Name":"Ashley", "Age":31, "History":"EVERY MORNING I[...]"}

You can do whatever you like with this data in your function - forms can be used
to set data on a character, to help builders create objects, or for players to
craft items or perform other complicated actions with many variables involved.

The data that your form will accept can also be specified in your form template -
let's say, for example, that you won't accept ages under 18 or over 100. You can
do this by specifying "min" and "max" values in your field's dictionary:

    PROFILE_TEMPLATE = [
    {"fieldname":"Name", "fieldtype":"text"},
    {"fieldname":"Age", "fieldtype":"number", "min":18, "max":100},
    {"fieldname":"History", "fieldtype":"text"}
    ]

Now if the player tries to enter a value out of range, the form will not acept the
given value.

    > age = 10
    Field 'Age' reqiures a minimum value of 18.
    > age = 900
    Field 'Age' has a maximum value of 100.

Setting 'min' and 'max' for a text field will instead act as a minimum or
maximum character length for the player's input.

There are lots of ways to present the form to the player - fields can have default
values or show a custom message in place of a blank value, and player input can be
verified by a custom function, allowing for a great deal of flexibility. There
is also an option for 'bool' fields, which accept only a True / False input and
can be customized to represent the choice to the player however you like (E.G.
Yes/No, On/Off, Enabled/Disabled, etc.)

This module contains a simple example form that demonstrates all of the included
functionality - a command that allows a player to compose a message to another
online character and have it send after a custom delay. You can test it by
importing this module in your game's default_cmdsets.py module and adding
CmdTestMenu to your default character's command set.

FIELD TEMPLATE KEYS:
Required:
    fieldname (str): Name of the field, as presented to the player.
    fieldtype (str): Type of value required: 'text', 'number', or 'bool'.

Optional:
    max (int): Maximum character length (if text) or value (if number).
    min (int): Minimum charater length (if text) or value (if number).
    truestr (str): String for a 'True' value in a bool field.
        (E.G. 'On', 'Enabled', 'Yes')
    falsestr (str): String for a 'False' value in a bool field.
        (E.G. 'Off', 'Disabled', 'No')
    default (str): Initial value (blank if not given).
    blankmsg (str): Message to show in place of value when field is blank.
    cantclear (bool): Field can't be cleared if True.
    required (bool): If True, form cannot be submitted while field is blank.
    verifyfunc (callable): Name of a callable used to verify input - takes
        (caller, value) as arguments. If the function returns True,
        the player's input is considered valid - if it returns False,
        the input is rejected. Any other value returned will act as
        the field's new value, replacing the player's input. This
        allows for values that aren't strings or integers (such as
        object dbrefs). For boolean fields, return '0' or '1' to set
        the field to False or True.
"""

from evennia import Command
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import delay, evmenu, evtable, list_to_string, logger


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


def init_fill_field(
    formtemplate,
    caller,
    formcallback,
    pretext="",
    posttext="",
    submitcmd="submit",
    borderstyle="cells",
    formhelptext=None,
    persistent=False,
    initial_formdata=None,
):
    """
    Initializes a menu presenting a player with a fillable form - once the form
    is submitted, the data will be passed as a dictionary to your chosen
    function.

    Args:
        formtemplate (list of dicts): The template for the form's fields.
        caller (obj): Player who will be filling out the form.
        formcallback (callable): Function to pass the completed form's data to.

    Options:
        pretext (str): Text to put before the form in the menu.
        posttext (str): Text to put after the form in the menu.
        submitcmd (str): Command used to submit the form.
        borderstyle (str): Form's EvTable border style.
        formhelptext (str): Help text for the form menu (or default is provided).
        persistent (bool): Whether to make the EvMenu persistent across reboots.
        initial_formdata (dict): Initial data for the form - a blank form with
            defaults specified in the template will be generated otherwise.
            In the case of a form used to edit properties on an object or a
            similar application, you may want to generate the initial form
            data dynamically before calling init_fill_field.
    """

    # Initialize form data from the template if none provided
    formdata = form_template_to_dict(formtemplate)
    if initial_formdata:
        formdata = initial_formdata

    # Provide default help text if none given
    if formhelptext is None:
        formhelptext = (
            "Available commands:|/"
            "|w<field> = <new value>:|n Set given field to new value, replacing the old value|/"
            "|wclear <field>:|n Clear the value in the given field, making it blank|/"
            "|wlook|n: Show the form's current values|/"
            "|whelp|n: Display this help screen|/"
            "|wquit|n: Quit the form menu without submitting|/"
            "|w%s|n: Submit this form and quit the menu" % submitcmd
        )

    # Pass kwargs to store data needed in the menu
    kwargs = {
        "formdata": formdata,
        "formtemplate": formtemplate,
        "formcallback": formcallback,
        "pretext": pretext,
        "posttext": posttext,
        "submitcmd": submitcmd,
        "borderstyle": borderstyle,
        "formhelptext": formhelptext,
    }

    # Initialize menu of selections
    FieldEvMenu(
        caller,
        "evennia.contrib.utils.fieldfill",
        startnode="menunode_fieldfill",
        auto_look=False,
        persistent=persistent,
        **kwargs,
    )


def menunode_fieldfill(caller, raw_string, **kwargs):
    """
    This is an EvMenu node, which calls itself over and over in order to
    allow a player to enter values into a fillable form. When the form is
    submitted, the form data is passed to a callback as a dictionary.
    """

    # Retrieve menu info - taken from ndb if not persistent or db if persistent
    if not caller.db._menutree:
        formdata = caller.ndb._menutree.formdata
        formtemplate = caller.ndb._menutree.formtemplate
        formcallback = caller.ndb._menutree.formcallback
        pretext = caller.ndb._menutree.pretext
        posttext = caller.ndb._menutree.posttext
        submitcmd = caller.ndb._menutree.submitcmd
        borderstyle = caller.ndb._menutree.borderstyle
        formhelptext = caller.ndb._menutree.formhelptext
    else:
        formdata = caller.db._menutree.formdata
        formtemplate = caller.db._menutree.formtemplate
        formcallback = caller.db._menutree.formcallback
        pretext = caller.db._menutree.pretext
        posttext = caller.db._menutree.posttext
        submitcmd = caller.db._menutree.submitcmd
        borderstyle = caller.db._menutree.borderstyle
        formhelptext = caller.db._menutree.formhelptext

    # Syntax error
    syntax_err = (
        "Syntax: <field> = <new value>|/Or: clear <field>, help, look, quit|/'%s' to submit form"
        % submitcmd
    )

    # Display current form data
    text = (
        display_formdata(
            formtemplate, formdata, pretext=pretext, posttext=posttext, borderstyle=borderstyle
        ),
        formhelptext,
    )
    options = {"key": "_default", "goto": "menunode_fieldfill"}

    if raw_string:
        # Test for given 'submit' command
        if raw_string.lower().strip() == submitcmd:
            # Test to see if any blank fields are required
            blank_and_required = []
            for field in formtemplate:
                if "required" in field.keys():
                    # If field is required but current form data for field is blank
                    if field["required"] is True and formdata[field["fieldname"]] is None:
                        # Add to blank and required fields
                        blank_and_required.append(field["fieldname"])
            if len(blank_and_required) > 0:
                # List the required fields left empty to the player
                caller.msg(
                    "The following blank fields require a value: %s"
                    % list_to_string(blank_and_required)
                )
                text = (None, formhelptext)
                return text, options

            # If everything checks out, pass form data to the callback and end the menu!
            try:
                formcallback(caller, formdata)
            except Exception:
                logger.log_trace("Error in fillable form callback.")
            return None, None

        # Test for 'look' command
        if raw_string.lower().strip() == "look" or raw_string.lower().strip() == "l":
            return text, options

        # Test for 'clear' command
        cleartest = raw_string.lower().strip().split(" ", 1)
        if cleartest[0].lower() == "clear":
            text = (None, formhelptext)
            if len(cleartest) < 2:
                caller.msg(syntax_err)
                return text, options
            matched_field = None

            for key in formdata.keys():
                if cleartest[1].lower() in key.lower():
                    matched_field = key

            if not matched_field:
                caller.msg("Field '%s' does not exist!" % cleartest[1])
                text = (None, formhelptext)
                return text, options

            # Test to see if field can be cleared
            for field in formtemplate:
                if field["fieldname"] == matched_field and "cantclear" in field.keys():
                    if field["cantclear"] is True:
                        caller.msg("Field '%s' can't be cleared!" % matched_field)
                        text = (None, formhelptext)
                        return text, options

            # Clear the field
            formdata.update({matched_field: None})
            caller.ndb._menutree.formdata = formdata
            caller.msg("Field '%s' cleared." % matched_field)
            return text, options

        if "=" not in raw_string:
            text = (None, formhelptext)
            caller.msg(syntax_err)
            return text, options

        # Extract field name and new field value
        entry = raw_string.split("=", 1)
        fieldname = entry[0].strip()
        newvalue = entry[1].strip()

        # Syntax error if field name is too short or blank
        if len(fieldname) < 1:
            caller.msg(syntax_err)
            text = (None, formhelptext)
            return text, options

        # Attempt to match field name to field in form data
        matched_field = None
        for key in formdata.keys():
            if fieldname.lower() in key.lower():
                matched_field = key

        # No matched field
        if matched_field is None:
            caller.msg("Field '%s' does not exist!" % fieldname)
            text = (None, formhelptext)
            return text, options

        # Set new field value if match
        # Get data from template
        fieldtype = None
        max_value = None
        min_value = None
        truestr = "True"
        falsestr = "False"
        verifyfunc = None
        for field in formtemplate:
            if field["fieldname"] == matched_field:
                fieldtype = field["fieldtype"]
                if "max" in field.keys():
                    max_value = field["max"]
                if "min" in field.keys():
                    min_value = field["min"]
                if "truestr" in field.keys():
                    truestr = field["truestr"]
                if "falsestr" in field.keys():
                    falsestr = field["falsestr"]
                if "verifyfunc" in field.keys():
                    verifyfunc = field["verifyfunc"]

        # Field type text verification
        if fieldtype == "text":
            # Test for max/min
            if max_value is not None:
                if len(newvalue) > max_value:
                    caller.msg(
                        "Field '%s' has a maximum length of %i characters."
                        % (matched_field, max_value)
                    )
                    text = (None, formhelptext)
                    return text, options
            if min_value is not None:
                if len(newvalue) < min_value:
                    caller.msg(
                        "Field '%s' reqiures a minimum length of %i characters."
                        % (matched_field, min_value)
                    )
                    text = (None, formhelptext)
                    return text, options

        # Field type number verification
        if fieldtype == "number":
            try:
                newvalue = int(newvalue)
            except:
                caller.msg("Field '%s' requires a number." % matched_field)
                text = (None, formhelptext)
                return text, options
            # Test for max/min
            if max_value is not None:
                if newvalue > max_value:
                    caller.msg("Field '%s' has a maximum value of %i." % (matched_field, max_value))
                    text = (None, formhelptext)
                    return text, options
            if min_value is not None:
                if newvalue < min_value:
                    caller.msg(
                        "Field '%s' reqiures a minimum value of %i." % (matched_field, min_value)
                    )
                    text = (None, formhelptext)
                    return text, options

        # Field type bool verification
        if fieldtype == "bool":
            if newvalue.lower() != truestr.lower() and newvalue.lower() != falsestr.lower():
                caller.msg(
                    "Please enter '%s' or '%s' for field '%s'." % (truestr, falsestr, matched_field)
                )
                text = (None, formhelptext)
                return text, options
            if newvalue.lower() == truestr.lower():
                newvalue = True
            elif newvalue.lower() == falsestr.lower():
                newvalue = False

        # Call verify function if present
        if verifyfunc:
            if verifyfunc(caller, newvalue) is False:
                # No error message is given - should be provided by verifyfunc
                text = (None, formhelptext)
                return text, options
            elif verifyfunc(caller, newvalue) is not True:
                newvalue = verifyfunc(caller, newvalue)
                # Set '0' or '1' to True or False if the field type is bool
                if fieldtype == "bool":
                    if newvalue == 0:
                        newvalue = False
                    elif newvalue == 1:
                        newvalue = True

        # If everything checks out, update form!!
        formdata.update({matched_field: newvalue})
        caller.ndb._menutree.formdata = formdata

        # Account for truestr and falsestr when updating a boolean form
        announced_newvalue = newvalue
        if newvalue is True:
            announced_newvalue = truestr
        elif newvalue is False:
            announced_newvalue = falsestr

        # Announce the new value to the player
        caller.msg("Field '%s' set to: %s" % (matched_field, str(announced_newvalue)))
        text = (None, formhelptext)

    return text, options


def form_template_to_dict(formtemplate):
    """
    Initializes a dictionary of form data from the given list-of-dictionaries
    form template, as formatted above.

    Args:
        formtemplate (list of dicts): Tempate for the form to be initialized.

    Returns:
        formdata (dict): Dictionary of initalized form data.
    """
    formdata = {}

    for field in formtemplate:
        # Value is blank by default
        fieldvalue = None
        if "default" in field:
            # Add in default value if present
            fieldvalue = field["default"]
        formdata.update({field["fieldname"]: fieldvalue})

    return formdata


def display_formdata(formtemplate, formdata, pretext="", posttext="", borderstyle="cells"):
    """
    Displays a form's current data as a table. Used in the form menu.

    Args:
        formtemplate (list of dicts): Template for the form
        formdata (dict): Form's current data

    Options:
        pretext (str): Text to put before the form table.
        posttext (str): Text to put after the form table.
        borderstyle (str): EvTable's border style.
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
        if formdata[field["fieldname"]] is not None:
            new_fieldvalue = str(formdata[field["fieldname"]])
        # Use blank message if field is blank and once is present
        if new_fieldvalue is None and "blankmsg" in field:
            new_fieldvalue = "|x" + str(field["blankmsg"]) + "|n"
        elif new_fieldvalue is None:
            new_fieldvalue = " "
        # Replace True and False values with truestr and falsestr from template
        if formdata[field["fieldname"]] is True and "truestr" in field:
            new_fieldvalue = field["truestr"]
        elif formdata[field["fieldname"]] is False and "falsestr" in field:
            new_fieldvalue = field["falsestr"]
        # Add name and value to table
        formtable.add_row(new_fieldname, new_fieldvalue)

    formtable.reformat_column(0, align="r", width=field_name_width)

    return pretext + "|/" + str(formtable) + "|/" + posttext


# EXAMPLE FUNCTIONS / COMMAND STARTS HERE


def verify_online_player(caller, value):
    """
    Example 'verify function' that matches player input to an online character
    or else rejects their input as invalid.

    Args:
        caller (obj): Player entering the form data.
        value (str): String player entered into the form, to be verified.

    Returns:
        matched_character (obj or False): dbref to a currently logged in
            character object - reference to the object will be stored in
            the form instead of a string. Returns False if no match is
            made.
    """
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

    # Returning anything besides True or False will replace the player's input with the returned
    # value. In this case, the value becomes a reference to the character object. You can store data
    # besides strings and integers in the 'formdata' dictionary this way!
    return matched_character


# Form template for the example 'delayed message' form
SAMPLE_FORM = [
    {
        "fieldname": "Character",
        "fieldtype": "text",
        "max": 30,
        "blankmsg": "(Name of an online player)",
        "required": True,
        "verifyfunc": verify_online_player,
    },
    {
        "fieldname": "Delay",
        "fieldtype": "number",
        "min": 3,
        "max": 30,
        "default": 10,
        "cantclear": True,
    },
    {
        "fieldname": "Message",
        "fieldtype": "text",
        "min": 3,
        "max": 200,
        "blankmsg": "(Message up to 200 characters)",
    },
    {
        "fieldname": "Anonymous",
        "fieldtype": "bool",
        "truestr": "Yes",
        "falsestr": "No",
        "default": False,
    },
]


class CmdTestMenu(Command):
    """
    This test command will initialize a menu that presents you with a form.
    You can fill out the fields of this form in any order, and then type in
    'send' to send a message to another online player, which will reach them
    after a delay you specify.

    Usage:
       <field> = <new value>
       clear <field>
       help
       look
       quit
       send
    """

    key = "testmenu"

    def func(self):
        """
        This performs the actual command.
        """
        pretext = (
            "|cSend a delayed message to another player ---------------------------------------|n"
        )
        posttext = (
            "|c--------------------------------------------------------------------------------|n|/"
            "Syntax: type |c<field> = <new value>|n to change the values of the form. Given|/"
            "player must be currently logged in, delay is given in seconds. When you are|/"
            "finished, type '|csend|n' to send the message.|/"
        )

        init_fill_field(
            SAMPLE_FORM,
            self.caller,
            init_delayed_message,
            pretext=pretext,
            posttext=posttext,
            submitcmd="send",
            borderstyle="none",
        )


def sendmessage(obj, text):
    """
    Callback to send a message to a player.

    Args:
        obj (obj): Player to message.
        text (str): Message.
    """
    obj.msg(text)


def init_delayed_message(caller, formdata):
    """
    Initializes a delayed message, using data from the example form.

    Args:
        caller (obj): Character submitting the message.
        formdata (dict): Data from submitted form.
    """
    # Retrieve data from the filled out form.
    # We stored the character to message as an object ref using a verifyfunc
    # So we don't have to do any more searching or matching here!
    player_to_message = formdata["Character"]
    message_delay = formdata["Delay"]
    sender = str(caller)
    if formdata["Anonymous"] is True:
        sender = "anonymous"
    message = ("Message from %s: " % sender) + str(formdata["Message"])

    caller.msg("Message sent to %s!" % player_to_message)
    # Make a deferred call to 'sendmessage' above.
    delay(message_delay, sendmessage, player_to_message, message)
    return
