from django.db import models

# Create your models here.
class Login(models.Model):
    pid = models.ForeignKey('players.PlayerDB')
    type = models.CharField(max_length=200)
    date = models.DateTimeField(auto_now_add=True)
    ip = models.CharField(max_length=200)
    result = models.CharField(max_length=200)