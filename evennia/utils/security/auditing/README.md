# Input/Output Auditing

Contrib - Johnny 2017

This is a tap that optionally intercepts all data sent to/from clients and the
server and passes it to a callback of your choosing.

It is intended for quality assurance, post-incident investigations and debugging
but obviously can be abused. All data is recorded in cleartext. Please
be ethical, and if you are unwilling to properly deal with the implications of
recording user passwords or private communications, please do not enable
this module.

Some checks have been implemented to protect the privacy of users.


Files included in this module:

    outputs.py - Example callback methods. This module ships with examples of
            callbacks that send data as JSON to a file in your game/server/logs
            dir or to your native Linux syslog daemon. You can of course write
            your own to do other things like post them to Kafka topics.

    server.py - Extends the Evennia ServerSession object to pipe data to the
            callback upon receipt.

	tests.py - Unit tests that check to make sure commands with sensitive
	        arguments are having their PII scrubbed.


Installation/Configuration:

Deployment is completed by configuring a few settings in server.conf. This line
is required:

    SERVER_SESSION_CLASS = 'evennia.contrib.security.auditing.server.AuditedServerSession'

This tells Evennia to use this ServerSession instead of its own. Below are the
other possible options along with the default value that will be used if unset.

    # Where to send logs? Define the path to a module containing your callback
    # function. It should take a single dict argument as input
    AUDIT_CALLBACK = 'evennia.contrib.security.auditing.outputs.to_file'

    # Log user input? Be ethical about this; it will log all private and
    # public communications between players and/or admins (default: False).
    AUDIT_IN = False

    # Log server output? This will result in logging of ALL system
    # messages and ALL broadcasts to connected players, so on a busy game any
    # broadcast to all users will yield a single event for every connected user!
    AUDIT_OUT = False

    # The default output is a dict. Do you want to allow key:value pairs with
    # null/blank values? If you're just writing to disk, disabling this saves
    # some disk space, but whether you *want* sparse values or not is more of a
    # consideration if you're shipping logs to a NoSQL/schemaless database.
    # (default: False)
    AUDIT_ALLOW_SPARSE = False

    # If you write custom commands that handle sensitive data like passwords,
    # you must write a regular expression to remove that before writing to log.
    # AUDIT_MASKS is a list of dictionaries that define the names of commands
    # and the regexes needed to scrub them.
    # The system already has defaults to filter out sensitive login/creation
    # commands in the default command set. Your list of AUDIT_MASKS will be appended
    # to those defaults.
    #
    # In the regex, the sensitive data itself must be captured in a named group with a
    # label of 'secret' (see the Python docs on the `re` module for more info). For
    # example: `{'authentication': r"^@auth\s+(?P<secret>[\w]+)"}`
    AUDIT_MASKS = []
