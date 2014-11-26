from django.db import models
import datetime
from django.utils.timezone import utc

now = datetime.datetime.utcnow().replace(tzinfo=utc)

# Create your models here.
class Descfile(models.Model):
    cid = models.ForeignKey('objects.ObjectDB')
    title = models.CharField(max_length=30)
    text = models.TextField()
    seton = models.DateTimeField(default=now)