"""
This describes the menu structure/logic of the OLC system editor, using the EvMenu subsystem. The
various nodes are modular and will when possible make use of the various utilities of the OLC rather
than hard-coding things in each node.

Menu structure:

    start:
        new object
        edit object <dbref>
        manage prototypes
        export session to batchcode file (immortals only)

        new/edit object:
            Protoype
            Typeclass
            Key
            Location
            Destination
            PErmissions
            LOcks
            Attributes
            TAgs
            Scripts

            create/update object
            copy object
            save prototype
            save/delete object
            update existing objects

        manage prototypes
            list prototype
            search prototype
            import prototype (from global store)

        export session

"""

def node_top(caller, raw_input):
    # top level node
    # links to edit, manage, export
    text = """OnLine Creation System"""
    options = ({"key": ("|yN|new", "new", "n"),
                "desc": "New object",
                "goto": "node_new_top",
                "exec": _obj_to_prototype},
               {"key": ("|yE|ndit", "edit", "e", "m"),
                "desc": "Edit existing object",
                "goto": "node_edit_top",
                "exec": _obj_to_prototype},
               {"key": ("|yP|nrototype", "prototype", "manage", "p", "m"),
                "desc": "Manage prototypes",
                "goto": "node_prototype_top"},
               {"key": ("E|yx|nport", "export", "x"),
                "desc": "Export to prototypes",
                "goto": "node_prototype_top"},
               {"key": ("|yQ|nuit", "quit", "q"),
                "desc": "Quit OLC",
                "goto": "node_quit"},)
    return text, options

def node_quit(caller, raw_input):
    return 'Exiting.', None

def node_new_top(caller, raw_input):
    pass

def node_edit_top(caller, raw_input):
    # edit top level
    text = """Edit object"""


def node_prototype_top(caller, raw_input):
    # manage prototypes
    pass


def node_export_top(caller, raw_input):
    # export top level
    pass

