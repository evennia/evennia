"""
Player command alias management stuff.
"""
from src.config.models import CommandAlias

CMD_ALIAS_LIST = {}
def load_cmd_aliases():
    """
    Load up our command aliases.
    """
    alias_list = CommandAlias.objects.all()
    
    # Reset the list.
    CMD_ALIAS_LIST = {}
    
    for alias in alias_list:
        CMD_ALIAS_LIST[alias.user_input] = alias.equiv_command
    
    print ' Command Aliases Loaded: %i' % (len(CMD_ALIAS_LIST),)