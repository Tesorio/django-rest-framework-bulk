from __future__ import print_function, unicode_literals

from django.db import models


class SimpleModel(models.Model):
    number = models.IntegerField()
    contents = models.CharField(max_length=16)
