from __future__ import unicode_literals

from django.db import models
import re
import datetime

# Create your models here.
class Server(models.Model):
    name = models.CharField(max_length=50, unique=True)
    url = models.CharField(max_length=255, unique=True)
    http_headers = models.TextField()
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name

class Profile(models.Model):
    name = models.CharField(max_length=50)
    http_post_payload = models.TextField()
    active = models.BooleanField(default=True)
    server = models.ForeignKey(Server)

    def save(self, *args, **kwargs):
        self.http_post_payload = re.sub("[a-zA-Z0-9_\$]+\|$", "{}|", 
            self.http_post_payload)
        return super(Profile, self).save(*args, **kwargs)

    def __unicode__(self):
        return "{} on {}".format(self.name, self.server)
    
    class Meta:
        unique_together = ("name", "server")
        
class Result(models.Model):
    report_time = models.DateTimeField()
    test_vm = models.CharField(max_length=50)
    test_spec = models.CharField(max_length=20)
    total_iops = models.FloatField()
    read_iops = models.FloatField()
    write_iops = models.FloatField()
    min_read_latency = models.FloatField()
    max_read_latency = models.FloatField()
    avg_read_latency = models.FloatField()
    min_write_latency = models.FloatField()
    max_write_latency = models.FloatField()
    avg_write_latency = models.FloatField()
    server = models.ForeignKey(Server)
    
    def __unicode__(self):
        date_time_format = "%Y-%m-%d %H:%M:%S"
        return "{}-{} test on {}".format(self.test_vm, self.test_spec, 
            datetime.datetime.strftime(self.report_time, date_time_format))
    
    class Meta:
        unique_together = ("report_time", "test_vm")