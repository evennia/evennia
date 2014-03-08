from django.db import models
from .. lib.penn import utcnow

# Create your models here.

class Pose(models.Model):
    cid = models.ForeignKey('objects.ObjectDB',related_name="poseset")
    seton = models.DateTimeField(default=utcnow())
    text = models.TextField()
    loc = models.ForeignKey('objects.ObjectDB')