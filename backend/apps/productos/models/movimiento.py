from django.db import models
from apps.core.models import BaseModel

class TipoMovimiento(models.TextChoices):
    ENTRADA = "ENTRADA", "Entrada"
    SALIDA = "SALIDA", "Salida"
    

class MovimientoInventario(BaseModel):
    producto = models.ForeignKey(
        "productos.Producto", 
        on_delete=models.CASCADE, 
        related_name="movimientos"
    )
    tipo = models.CharField(
        max_length=10, 
        choices=TipoMovimiento.choices
    )
    cantidad = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Cantidad del movimiento (siempre positiva, el tipo indica dirección)"
    )
    stock_anterior = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        editable=False
    )
    stock_nuevo = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        editable=False
    )
    referencia = models.CharField(
        max_length=150, 
        help_text="Ej: Factura #50, Ajuste por inventario anual"
    )

    class Meta:
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"
        ordering = ["-creado_en"]


    def __str__(self):
        return f"{self.tipo.upper()} - {self.producto.nombre} ({self.cantidad})"