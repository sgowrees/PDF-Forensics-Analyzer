from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        USER = "user", "User"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
    )

    def is_admin_user(self):
        return self.role == self.Role.ADMIN