from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class TipoDocumentoVenta(models.TextChoices):
    PEDIDO = "PEDIDO", "Pedido de Venta"
    GUIA = "GUIA", "Guía de Despacho"
    FACTURA = "FACTURA", "Factura de Venta"
    NOTA_CREDITO = "NOTA_CREDITO", "Nota de Crédito"


class VentaHistorial(BaseModel):
    """Historial de cambios de estado para documentos del módulo ventas."""

    tipo_documento = models.CharField(
        max_length=20,
        choices=TipoDocumentoVenta.choices,
    )

    documento_id = models.UUIDField(
        help_text="ID del documento al que pertenece este registro de historial.",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventas_historial",
    )

    estado_anterior = models.CharField(max_length=30)
    estado_nuevo = models.CharField(max_length=30)
    motivo = models.TextField(blank=True)
    cambios = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "tipo_documento", "documento_id"]),
            models.Index(fields=["empresa", "creado_en"]),
        ]
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.tipo_documento} {self.documento_id} → {self.estado_nuevo}"
