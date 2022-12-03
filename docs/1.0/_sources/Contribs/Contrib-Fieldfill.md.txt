# Easy fillable form

Contribution by Tim Ashley Jenkins, 2018

This module contains a function that generates an `EvMenu` for you - this
menu presents the player with a form of fields that can be filled
out in any order (e.g. for character generation or building). Each field's value can 
be verified, with the function allowing easy checks for text and integer input, 
minimum and maximum values / character lengths, or can even be verified by a custom 
function. Once the form is submitted, the form's data is submitted as a dictionary 
to any callable of your choice.

## Usage

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

```
      Name:
       Age:
   History:
```

While in this menu, the player can assign a new value to any field with the
syntax <field> = <new value>, like so:

```
    > name = Ashley
    Field 'Name' set to: Ashley
```

Typing 'look' by itself will show the form and its current values.

```
    > look

      Name: Ashley
       Age:
    History:
```

Number fields require an integer input, and will reject any text that can't
be converted into an integer.

```
    > age = youthful
    Field 'Age' requires a number.
    > age = 31
    Field 'Age' set to: 31
```

Form data is presented as an EvTable, so text of any length will wrap cleanly.

```
    > history = EVERY MORNING I WAKE UP AND OPEN PALM SLAM[...]
    Field 'History' set to: EVERY MORNING I WAKE UP AND[...]
    > look

      Name: Ashley
       Age: 31
   History: EVERY MORNING I WAKE UP AND OPEN PALM SLAM A VHS INTO THE SLOT.
            IT'S CHRONICLES OF RIDDICK AND RIGHT THEN AND THERE I START DOING
            THE MOVES ALONGSIDE WITH THE MAIN CHARACTER, RIDDICK. I DO EVERY
            MOVE AND I DO EVERY MOVE HARD.
```

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

```
    PROFILE_TEMPLATE = [
    {"fieldname":"Name", "fieldtype":"text"},
    {"fieldname":"Age", "fieldtype":"number", "min":18, "max":100},
    {"fieldname":"History", "fieldtype":"text"}
    ]
```

Now if the player tries to enter a value out of range, the form will not acept the
given value.

```
    > age = 10
    Field 'Age' reqiures a minimum value of 18.
    > age = 900
    Field 'Age' has a maximum value of 100.
```

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
importing this module in your game's `default_cmdsets.py` module and adding
CmdTestMenu to your default character's command set.

## FIELD TEMPLATE KEYS:

### Required:

```
    fieldname (str): Name of the field, as presented to the player.
    fieldtype (str): Type of value required: 'text', 'number', or 'bool'.
```

### Optional:

- max (int): Maximum character length (if text) or value (if number).
- min (int): Minimum charater length (if text) or value (if number).
- truestr (str): String for a 'True' value in a bool field.
  (E.G. 'On', 'Enabled', 'Yes')
- falsestr (str): String for a 'False' value in a bool field.
  (E.G. 'Off', 'Disabled', 'No')
- default (str): Initial value (blank if not given).
- blankmsg (str): Message to show in place of value when field is blank.
- cantclear (bool): Field can't be cleared if True.
- required (bool): If True, form cannot be submitted while field is blank.
- verifyfunc (callable): Name of a callable used to verify input - takes
  (caller, value) as arguments. If the function returns True,
  the player's input is considered valid - if it returns False,
  the input is rejected. Any other value returned will act as
  the field's new value, replacing the player's input. This
  allows for values that aren't strings or integers (such as
  object dbrefs). For boolean fields, return '0' or '1' to set
  the field to False or True.


----

<small>This document page is generated from `evennia/contrib/utils/fieldfill/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
