from django.db import models

from apps.core.models import BaseModel


class EstadoSerie(models.TextChoices):
    DISPONIBLE = "DISPONIBLE", "Disponible"
    SALIDA = "SALIDA", "Salida"


class StockSerie(BaseModel):
    """Unidad serializada para trazabilidad individual de inventario."""

    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.CASCADE,
        related_name="series",
    )
    bodega = models.ForeignKey(
        "inventario.Bodega",
        on_delete=models.CASCADE,
        related_name="series",
    )
    serie_codigo = models.CharField(max_length=120)
    lote_codigo = models.CharField(max_length=80, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=EstadoSerie.choices, default=EstadoSerie.DISPONIBLE)
    movimiento_entrada = models.ForeignKey(
        "inventario.MovimientoInventario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="series_entrada",
    )
    movimiento_salida = models.ForeignKey(
        "inventario.MovimientoInventario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="series_salida",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "producto", "serie_codigo"],
                name="uniq_serie_producto_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "producto", "estado"]),
            models.Index(fields=["empresa", "serie_codigo"]),
        ]
