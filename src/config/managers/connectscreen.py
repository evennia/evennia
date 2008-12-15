"""
Custom manager for ConnectScreen objects.
"""
from django.db import models

class ConnectScreenManager(models.Manager):
    def get_random_connect_screen(self):
        """
        Returns a random active connect screen.
        """
        try:
            return self.filter(is_active=True).order_by('?')[0]
        except IndexError:
            new_screen = ConnectScreen(name='Default', 
                connect_screen_text='This is a placeholder connect screen. Remind your admin to edit it through the Admin interface.')
            new_screen.save()
            return new_screen
