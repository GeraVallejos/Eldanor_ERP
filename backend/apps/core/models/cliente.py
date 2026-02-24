from django.db import models
from core.models import BaseModel

class Cliente(BaseModel):
    # DATOS BÁSICOS
    nombre = models.CharField(max_length=255)
    razon_social = models.CharField(max_length=255, blank=True, null=True)
    tipo = models.CharField(
        max_length=20,
        choices=(('persona', 'Persona'), ('empresa', 'Empresa')),
        default='persona'
    )
    rut = models.CharField(max_length=12, blank=True, null=True, help_text="RUT/DNI")
    
    # CONTACTO
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    celular = models.CharField(max_length=50, blank=True, null=True)
    
    # DIRECCIÓN
    direccion = models.TextField(blank=True, null=True)
    comuna = models.CharField(max_length=100, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    pais = models.CharField(max_length=100, blank=True, null=True, default='Chile')

    # DATOS FINANCIEROS
    limite_credito = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    condicion_pago = models.CharField(
        max_length=50,
        choices=(('contado', 'Contado'), ('30_dias', '30 días'), ('60_dias', '60 días')),
        default='contado'
    )
    
    # CATEGORÍAS / SEGMENTOS
    categoria_cliente = models.CharField(max_length=50, blank=True, null=True)
    segmento = models.CharField(max_length=50, blank=True, null=True)

    # METADATA / ESTADO
    activo = models.BooleanField(default=True)
    notas = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = (
            ('empresa', 'nombre'),
            ('empresa', 'rut'),
        )
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"
