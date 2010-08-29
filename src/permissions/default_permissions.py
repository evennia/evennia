"""
Setup the permission hierarchy and groups. This is
read once during server startup. Further groups and
permissions have to be added manually. 

To set up your own permission scheme, have
PERMISSION_SETUP_MODULE in game/settings point to
a module of your own. This module must define two global
dictionaries PERMS and GROUPS.

PERMS contains all permissions defined at server start
      on the form {key:desc, key:desc, ...}
GROUPS gathers permissions (which must have been
       previously created as keys in PERMS) into clusters
       on the form {groupname: [key, key, ...], ...}
"""

# Defining all permissions. 
PERMS = [
    'emit',
    'wall',

    'teleport',
    'setobjalias',
    'wipe',
    'set',
    'cpattr',
    'mvattr',
    'find',
    'create',
    'copy',
    'open',
    'link',
    'unlink',
    'dig',
    'desc',
    'destroy',
    'examine',
    'typeclass',
    'debug',
    
    'batchcommands',
    'batchcodes',
    
    'ccreate',
    'cdesc',
    'tell',
    'time',
    'list',

    'ps',
    'stats',   

    'reload',
    'py',
    'listscripts',
    'listcmdsets',
    'listobjects',
    'boot',
    'delplayer',
    'newpassword',
    'home',
    'service', 
    'shutdown',
    'perm',
    'sethelp',
]

# Permission Groups 
# Permission groups clump the previously defined permissions into
# larger chunks. {groupname: [permissionkey,... ]}

GROUPS = {    
    "Immortals": PERMS,
    "Wizards": [perm for perm in PERMS
                if perm not in ['shutdown', 
                                'py', 
                                'reload', 
                                'service', 
                                'perm',
                                'batchcommands',
                                'batchcodes']],
    
    "Builders": [perm for perm in PERMS
                 if perm not in ['shutdown', 
                                 'py', 
                                 'reload', 
                                 'service', 
                                 'perm',
                                 'batchcommands',
                                 'batchcodes',
                                 
                                 'wall',
                                 'boot',
                                 'delplayer',
                                 'newpassword']],
    "PlayerHelpers": ['tell',
                       'sethelp', 'ccreate', 'use_channels'],
    "Players": ['tell', 'ccreate', 'use_channels']
}
