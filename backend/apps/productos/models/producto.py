from django.db import models
from apps.core.models import BaseModel
from apps.productos.services.producto_validation import clean_producto
from apps.productos.validators import normalize_sku


class TipoProducto(models.TextChoices):
    PRODUCTO = "producto", "Producto físico"
    SERVICIO = "servicio", "Servicio"


class Producto(BaseModel):

    nombre = models.CharField(max_length=255)

    descripcion = models.TextField(blank=True)

    sku = models.CharField(
        max_length=100,
        help_text="Código interno del producto"
    )

    tipo = models.CharField(
        max_length=20,
        choices=TipoProducto.choices,
        default=TipoProducto.PRODUCTO
    )

    categoria = models.ForeignKey(
        "productos.Categoria",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="productos"
    )

    impuesto = models.ForeignKey(
        "productos.Impuesto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="productos"
    )

    precio_referencia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Precio sugerido o referencia"
    )

    precio_costo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    maneja_inventario = models.BooleanField(default=True)

    stock_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("empresa", "sku")
        indexes = [
            models.Index(fields=["empresa", "nombre"]),
            models.Index(fields=["empresa", "sku"]),
        ]

    def clean(self):
        clean_producto(self)

    def save(self, *args, **kwargs):

        # 1. Normalizacion de SKU
        # Se ejecuta justo antes de guardar en la DB.
        if self.sku:
            self.sku = normalize_sku(self.sku)
            
        if self.nombre:
            self.nombre = self.nombre.strip()

        # Regla estructural antes de validar
        if self.tipo == TipoProducto.SERVICIO:
            self.maneja_inventario = False
            self.stock_actual = 0

        super().save(*args, **kwargs)

    

    def __str__(self):
        return f"{self.nombre} ({self.sku})"
    