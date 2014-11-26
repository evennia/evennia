from django.db import models

# Create your models here.
class JobCat(models.Model):
    key = models.CharField(max_length=15,unique=True)
    key.primary_key = True
    priority = models.IntegerField(default=0)
    hidden = models.BooleanField(default=False)
    handlers = models.ManyToManyField('players.PlayerDB')
    
class Job(models.Model):
    priority = models.IntegerField(default=0)
    submitter = models.ForeignKey('players.PlayerDB')
    jobcat = models.ForeignKey('JobCat')
    submitted = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=1,default=" ")
    handlers = models.ManyToManyField('players.PlayerDB',related_name="assigned")
    jobtext = models.TextField()
    jobtitle = models.CharField(max_length=200)
    updated = models.DateTimeField(auto_now=True)
    
class JobComment(models.Model):
    jobid = models.ForeignKey('Job')
    submitter = models.ForeignKey('players.PlayerDB',null=True,blank=True,on_delete=models.SET_NULL)
    submitted = submitted = models.DateTimeField(auto_now_add=True)
    commenttext = models.TextField()

class JobLog(models.Model):
    jobid = models.ForeignKey('Job')
    submitter = models.ForeignKey('players.PlayerDB',null=True,blank=True,on_delete=models.SET_NULL)
    submitted = submitted = models.DateTimeField(auto_now_add=True)
    logtext = models.TextField()
    
class JobRead(models.Model):
    jobid = models.ForeignKey('Job')
    reader = models.ForeignKey('players.PlayerDB')
    readdate = models.DateTimeField(auto_now=True)
    
class JobVote(models.Model):
    jobid = models.ForeignKey('Job')
    voter = models.ForeignKey('players.PlayerDB',null=True,blank=True,on_delete=models.SET_NULL)
    submitted = models.DateTimeField(auto_now_add=True)
    vote = models.CharField(max_length=10)