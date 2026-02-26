import uuid
from django.db import models
from apps.core.validators import formatear_rut, normalizar_texto, validar_rut


class PoliticaPrecio(models.TextChoices):
        FIJO = "FIJO", "Precio Fijo"
        EDITABLE = "EDITABLE", "Precio Editable"


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
        ("free", "FREE"),
        ("basic", "BASIC"),
        ("pro", "PRO"),
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

    def save(self, *args, **kwargs):

        self.nombre = normalizar_texto(self.nombre)
        self.nombre_legal = normalizar_texto(self.nombre_legal)
        self.email = normalizar_texto(self.email, es_email=True)
        self.direccion = normalizar_texto(self.direccion)
        self.ciudad = normalizar_texto(self.ciudad)
        self.pais = normalizar_texto(self.pais)

        if self.rut:
            self.rut = formatear_rut(self.rut)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean() 

        if self.rut:
            self.rut = formatear_rut(self.rut)
            validar_rut(self.rut)

    def __str__(self):
        return self.nombre