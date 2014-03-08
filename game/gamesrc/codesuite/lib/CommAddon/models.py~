from django.db import models

# Create your models here.

class PlayCommConf(models.Model):
    chankey = models.ForeignKey('comms.Channel')
    pid = models.ForeignKey('players.PlayerDB')
    ptitle = models.CharField(max_length=200)
    muzzled = models.DateTimeField(null=True)
    muzzledby = models.ForeignKey('players.PlayerDB',null=True,blank=True,on_delete=models.SET_NULL,related_name="muzzleset")
    
class CharCommConf(models.Model):
    chankey = models.ForeignKey('comms.Channel')
    cid = models.ForeignKey('objects.ObjectDB')
    ctitle = models.CharField(max_length=200)
    
class ChanCommConf(models.Model):
    chankey = models.ForeignKey('comms.Channel')
    displaymode = models.IntegerField(default="0")
    color = models.CharField(max_length=20,default="n")
    titles = models.BooleanField(default=False)