from django.db import models

# Create your models here.
class InfoFile(models.Model):
    cid = models.ForeignKey('objects.ObjectDB')
    title = models.CharField(max_length=20)
    seton = models.DateTimeField(auto_now_add=True)
    text = models.TextField()
    setby = models.ForeignKey('players.PlayerDB',null=True,on_delete=models.SET_NULL)
    hidden = models.BooleanField(default=False)
    published = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)
    approvedby = models.ForeignKey('players.PlayerDB',null=True,on_delete=models.SET_NULL,related_name="infoappset")
    approvedon = models.DateTimeField(null=True)