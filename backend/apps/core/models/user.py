import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )


    email = models.EmailField(unique=True)

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="usuarios",
        null=True,
        blank=True
    )

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("vendedor", "Vendedor"),
        ("contador", "Contador"),
    ]

    rol = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="vendedor"
    )

    telefono = models.CharField(max_length=20, blank=True)

    activo = models.BooleanField(default=True)


    def __str__(self):
        return f"{self.email}"