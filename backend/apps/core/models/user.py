import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.validators import normalizar_texto


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
        ("OWNER", "Propietario"),
        ("ADMIN", "Administrador"),
        ("VENDEDOR", "Vendedor"),
        ("CONTADOR", "Contador"),
    ]

    rol = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="VENDEDOR"
    )

    telefono = models.CharField(max_length=20, blank=True)

    activo = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['username']

    def save(self, *args, **kwargs):
        # 1. Email a minúsculas (fundamental para evitar duplicados por error de tipeo)
        if self.email:
            self.email = normalizar_texto(self.email, es_email=True)
        
        # 2. Forzar que el username sea igual al email si no se usa
        if not self.username:
            self.username = self.email

        # 3. Nombres y Apellidos en MAYÚSCULAS
        if self.first_name:
            self.first_name = normalizar_texto(self.first_name)
        if self.last_name:
            self.last_name = normalizar_texto(self.last_name)

        super().save(*args, **kwargs)

    def __str__(self):
        # Una representación más amigable para el Admin
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.email})"
        return self.email