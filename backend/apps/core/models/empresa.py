import uuid
from django.db import models


class PoliticaPrecio(models.TextChoices):
        FIJO = "fijo", "Precio fijo"
        EDITABLE = "editable", "Precio editable"


class Empresa(models.Model):

    

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    politica_precio = models.CharField(
        max_length=20,
        choices=PoliticaPrecio.choices,
        default=PoliticaPrecio.FIJO
    )

    margen_minimo = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    nombre = models.CharField(max_length=150)
    nombre_legal = models.CharField(max_length=200, blank=True)
    rut = models.CharField(max_length=20, unique=True)

    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=250, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    pais = models.CharField(max_length=100, default="Chile")

    PLAN_CHOICES = [
        ("free", "Free"),
        ("basic", "Basic"),
        ("pro", "Pro"),
    ]

    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default="free"
    )

    activa = models.BooleanField(default=True)

    fecha_suscripcion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField(null=True, blank=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre