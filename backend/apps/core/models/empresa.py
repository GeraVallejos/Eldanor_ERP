import uuid
from django.db import models
from apps.core.validators import formatear_rut, normalizar_texto, validar_rut
from apps.core.storage.public_storage import PublicMediaStorage
from apps.core.utils.optimizador_imagen import optimize_image


class PoliticaPrecio(models.TextChoices):
        FIJO = "FIJO", "Precio Fijo"
        EDITABLE = "EDITABLE", "Precio Editable"


class Plan(models.TextChoices):
    FREE = "FREE", "Free"
    BASIC = "BASIC", "Basic"
    PRO = "PRO", "Pro"


class TipoEmpresa(models.TextChoices):
    CONSTRUCTORA = "CONSTRUCTORA", "Constructora"
    VETERINARIA = "VETERINARIA", "Veterinaria"
    GENERAL = "GENERAL", "General"


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

    logo = models.ImageField(
        storage=PublicMediaStorage(),
        null=True, 
        blank=True
    )

    nombre = models.CharField(max_length=150)
    nombre_legal = models.CharField(max_length=200, blank=True)
    rut = models.CharField(max_length=20, unique=True)

    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=250, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    pais = models.CharField(max_length=100, default="Chile")


    plan = models.CharField(
        max_length=20,
        choices=Plan.choices,
        default=Plan.FREE
    )

    tipo_empresa = models.CharField(
        max_length=20,
        choices=TipoEmpresa.choices,
        default=TipoEmpresa.GENERAL
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

        should_process_logo = False
        if self.logo:
            if not self.pk:
                should_process_logo = True
            else:
                previous_logo = (
                    self.__class__.objects
                    .filter(pk=self.pk)
                    .values_list('logo', flat=True)
                    .first()
                )
                current_logo = getattr(self.logo, 'name', '')
                should_process_logo = previous_logo != current_logo

        if should_process_logo:
            optimized = optimize_image(self.logo)
            # Keep one deterministic public logo per company to avoid cross-tenant overwrites.
            self.logo.save(f"empresas/{self.id}/logo.webp", optimized, save=False)

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