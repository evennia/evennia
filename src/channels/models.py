"""
Models for the help system.
"""
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User, Group
from src.objects.models import Object
from src.ansi import parse_ansi

class CommChannel(models.Model):
    """
    The CommChannel class represents a comsys channel in the vein of MUX/MUSH.
    """
    name = models.CharField(max_length=255)
    ansi_name = models.CharField(max_length=255)
    owner = models.ForeignKey(Object, related_name="channel_owner_set")
    description = models.CharField(max_length=80, blank=True, null=True)
    is_joined_by_default = models.BooleanField(default=False)
    req_grp = models.ManyToManyField(Group, blank=True, null=True)

    def __str__(self):
        return "%s" % (self.name,)
    
    class Meta:
        ordering = ['-name']
        permissions = settings.PERM_CHANNELS
    
    def get_name(self):
        """
        Returns a channel's name.
        """
        return self.name

    def get_header(self):
        """
        Returns the channel's header text, or what is shown before each channel
        message.
        """
        return parse_ansi(self.ansi_name)

    def get_owner(self):
        """
        Returns a channels' owner.
        """
        return self.owner

    def set_name(self, new_name):
        """
        Rename a channel
        """
        self.name = parse_ansi(new_name, strip_ansi=True)
        self.header = "[%s]" % (parse_ansi(new_name),)
        self.save()

    def set_header(self, new_header):
        """
        Sets a channel's header text.
        """
        self.header = parse_ansi(new_header)
        self.save()

    def set_owner(self, new_owner):
        """
        Sets a channel's owner.
        """
        self.owner = new_owner
        self.save()

    def set_description(self, new_description):
        """
        Sets a channel's description.
        """
        self.description = new_description
        self.save()
        
    def controlled_by(self, pobject):
        """
        Use this to see if another object controls the channel. This is means
        that the specified object either owns the channel or has special
        permissions to control it.
        
        pobject: (Object) Player object to check for control.
        """
        if pobject.is_superuser():
            return True
        
        if self.owner and self.owner.id == pobject.id: 
            # If said object owns the target, then give it the green.
            return True

        # They've failed to meet any of the above conditions.
        return False
    
    def get_default_chan_alias(self):
        """
        Returns a default channel alias for the channel if none is provided.
        """
        return self.name[:3].lower()
    
class CommChannelMembership(models.Model):
    """
    Used to track which channels an Object is listening to.
    """
    channel = models.ForeignKey(CommChannel, related_name="membership_set")
    listener = models.ForeignKey(Object, related_name="channel_membership_set")
    user_alias = models.CharField(max_length=10)
    comtitle = models.CharField(max_length=25, blank=True)
    is_listening = models.BooleanField(default=True)
    
    def __str__(self):
        return "%s: %s" % (self.channel.name, self.listener.name)

class CommChannelMessage(models.Model):
    """
    A single logged channel message.
    """
    channel = models.ForeignKey(CommChannel, related_name="msg_channel")
    message = models.TextField()
    date_sent = models.DateTimeField(editable=False, auto_now_add=True)

    class Meta:
        ordering = ['-date_sent']

    def __str__(self):
        return "%s: %s" % (self.channel.name, self.message)
    
