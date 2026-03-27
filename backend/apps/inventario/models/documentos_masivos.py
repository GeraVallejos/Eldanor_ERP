from django.db import models

from apps.core.models import BaseModel
from apps.documentos.models import DocumentoNumeradoBase


class EstadoDocumentoInventario(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    CONFIRMADO = "CONFIRMADO", "Confirmado"


class AjusteInventarioMasivo(DocumentoNumeradoBase):
    referencia = models.CharField(max_length=150)
    motivo = models.CharField(max_length=120)
    confirmado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado_en", "-id"]
        indexes = [
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["empresa", "numero"]),
            models.Index(fields=["empresa", "confirmado_en"]),
        ]


class AjusteInventarioMasivoItem(BaseModel):
    documento = models.ForeignKey(
        "inventario.AjusteInventarioMasivo",
        on_delete=models.CASCADE,
        related_name="items",
    )
    producto = models.ForeignKey("productos.Producto", on_delete=models.PROTECT, related_name="ajustes_masivos")
    bodega = models.ForeignKey(
        "inventario.Bodega",
        on_delete=models.PROTECT,
        related_name="ajustes_masivos",
        null=True,
        blank=True,
    )
    stock_objetivo = models.DecimalField(max_digits=12, decimal_places=2)
    stock_actual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    diferencia = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    movimiento = models.ForeignKey(
        "inventario.MovimientoInventario",
        on_delete=models.PROTECT,
        related_name="ajustes_masivos_items",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["creado_en", "id"]
        indexes = [
            models.Index(fields=["empresa", "documento"]),
            models.Index(fields=["empresa", "producto"]),
        ]


class TrasladoInventarioMasivo(DocumentoNumeradoBase):
    referencia = models.CharField(max_length=150)
    motivo = models.CharField(max_length=120)
    bodega_origen = models.ForeignKey(
        "inventario.Bodega",
        on_delete=models.PROTECT,
        related_name="traslados_masivos_origen",
    )
    bodega_destino = models.ForeignKey(
        "inventario.Bodega",
        on_delete=models.PROTECT,
        related_name="traslados_masivos_destino",
    )
    confirmado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado_en", "-id"]
        indexes = [
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["empresa", "numero"]),
            models.Index(fields=["empresa", "confirmado_en"]),
        ]


class TrasladoInventarioMasivoItem(BaseModel):
    documento = models.ForeignKey(
        "inventario.TrasladoInventarioMasivo",
        on_delete=models.CASCADE,
        related_name="items",
    )
    producto = models.ForeignKey("productos.Producto", on_delete=models.PROTECT, related_name="traslados_masivos")
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    movimiento_salida = models.ForeignKey(
        "inventario.MovimientoInventario",
        on_delete=models.PROTECT,
        related_name="traslados_masivos_salida_items",
        null=True,
        blank=True,
    )
    movimiento_entrada = models.ForeignKey(
        "inventario.MovimientoInventario",
        on_delete=models.PROTECT,
        related_name="traslados_masivos_entrada_items",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["creado_en", "id"]
        indexes = [
            models.Index(fields=["empresa", "documento"]),
            models.Index(fields=["empresa", "producto"]),
        ]
