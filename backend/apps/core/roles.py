from django.db import models

class RolUsuario(models.TextChoices):
    OWNER = "OWNER", "Propietario"
    ADMIN = "ADMIN", "Administrador"
    VENDEDOR = "VENDEDOR", "Vendedor"
    CONTADOR = "CONTADOR", "Contador"