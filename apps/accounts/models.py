from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    bio = models.TextField(blank=True)
    display_name = models.CharField(max_length=160, blank=True)

    def __str__(self):
        return self.display_name or self.username
