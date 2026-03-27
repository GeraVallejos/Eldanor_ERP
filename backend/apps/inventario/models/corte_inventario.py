from django.db import models

from apps.core.models import BaseModel
from apps.documentos.models import DocumentoNumeradoBase


class EstadoCorteInventario(models.TextChoices):
    GENERADO = "GENERADO", "Generado"


class TipoCorteInventario(models.TextChoices):
    MANUAL = "MANUAL", "Manual"
    CIERRE_MENSUAL = "CIERRE_MENSUAL", "Cierre mensual"


class CorteInventario(DocumentoNumeradoBase):
    tipo_corte = models.CharField(
        max_length=30,
        choices=TipoCorteInventario.choices,
        default=TipoCorteInventario.MANUAL,
    )
    periodo_referencia = models.CharField(max_length=7, blank=True, default="")
    fecha_corte = models.DateField()
    reservado_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    disponible_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    items_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-fecha_corte", "-creado_en", "-id"]
        indexes = [
            models.Index(fields=["empresa", "fecha_corte"]),
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["empresa", "numero"]),
            models.Index(fields=["empresa", "tipo_corte", "periodo_referencia"]),
        ]


class CorteInventarioItem(BaseModel):
    corte = models.ForeignKey(
        "inventario.CorteInventario",
        on_delete=models.CASCADE,
        related_name="items",
    )
    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        related_name="cortes_inventario",
    )
    bodega = models.ForeignKey(
        "inventario.Bodega",
        on_delete=models.PROTECT,
        related_name="cortes_inventario",
    )
    producto_nombre = models.CharField(max_length=255)
    producto_sku = models.CharField(max_length=120, blank=True, default="")
    producto_categoria_nombre = models.CharField(max_length=150, blank=True, default="")
    bodega_nombre = models.CharField(max_length=120)
    stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reservado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    disponible = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    costo_promedio = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    valor_stock = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    lotes_activos = models.CharField(max_length=500, blank=True, default="")
    proximo_vencimiento = models.DateField(null=True, blank=True)
    series_disponibles = models.PositiveIntegerField(default=0)
    series_muestra = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["producto_nombre", "bodega_nombre", "id"]
        indexes = [
            models.Index(fields=["empresa", "corte"]),
            models.Index(fields=["empresa", "producto"]),
            models.Index(fields=["empresa", "bodega"]),
        ]
