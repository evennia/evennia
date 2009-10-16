#
# Support command for editing command aliases
#
from src.config.models import CommandAlias

def add_alias(user_input, equiv_command):
        """
        Adds a new alias or replace an old one.
        """
        aquery = CommandAlias.objects.filter(user_input=user_input)
        if aquery:
            # overwrite existing alias
            alias = aquery[0]
            alias.user_input = user_input
            alias.equiv_command = equiv_command
            alias.save()
        else:
            # create new alias
            CommandAlias(user_input=user_input, equiv_command=equiv_command).save()

def del_alias(alias):
        """
        Delete an alias from the database
        """
        aquery = CommandAlias.objects.filter(user_input=alias)
        if aquery:           
            aquery[0].delete()
