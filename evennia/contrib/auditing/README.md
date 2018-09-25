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

Deployment is completed by configuring a few settings in server.conf. In short,
you must tell Evennia to use this ServerSession instead of its own, specify
which direction(s) you wish to record and where you want the data sent.

    SERVER_SESSION_CLASS = 'evennia.contrib.auditing.server.AuditedServerSession'
    
    # Where to send logs? Define the path to a module containing your callback
    # function. It should take a single dict argument as input.
    AUDIT_CALLBACK = 'evennia.contrib.auditing.outputs.to_file'
    
    # Log user input? Be ethical about this; it will log all private and 
    # public communications between players and/or admins.
    AUDIT_IN = True/False
    
    # Log server output? This will result in logging of ALL system
    # messages and ALL broadcasts to connected players, so on a busy game any
    # broadcast to all users will yield a single event for every connected user!
    AUDIT_OUT = True/False
    
    # The default output is a dict. Do you want to allow key:value pairs with
    # null/blank values? If you're just writing to disk, disabling this saves 
    # some disk space, but whether you *want* sparse values or not is more of a 
    # consideration if you're shipping logs to a NoSQL/schemaless database.
    AUDIT_ALLOW_SPARSE = True/False
    
    # If you write custom commands that handle sensitive data like passwords, 
    # you must write a regular expression to remove that before writing to log.
    # AUDIT_MASKS is a list of dictionaries that define the names of commands 
    # and the regexes needed to scrub them.
    #
    # The sensitive data itself must be captured in a named group with a
    # label of 'secret'.
    AUDIT_MASKS = [
        {'authentication': r"^@auth\s+(?P<secret>[\w]+)"},
    ]