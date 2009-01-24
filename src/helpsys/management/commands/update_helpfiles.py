from django.core.management.base import NoArgsCommand
from django.core.management.color import no_style
from django.core import management

class Command(NoArgsCommand):
    """
    Updates the database's copy of the help files from the fixtures located
    under evennia/game/docs/help_files.json.
    """
    option_list = NoArgsCommand.option_list
    help = "Updates (over-writes) your game's help files from the docs dir."
    def handle_noargs(self, **options):
        self.style = no_style()
        management.call_command('loaddata', 'docs/help_files.json', verbosity=1)
        print "Help files updated."
