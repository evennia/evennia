from django.db import models

class IPLog(models.Model):
    type = models.CharField(max_length=200)
    date = models.DateTimeField('date of login')
    ip = models.CharField(max_length=200)
    result = models.CharField(max_length=200)