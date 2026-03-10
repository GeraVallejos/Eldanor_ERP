from django.db import models
from apps.core.models import BaseModel
from apps.documentos.models import DocumentoReferenciaMixin, TipoDocumentoReferencia


class ReservaStock(DocumentoReferenciaMixin, BaseModel):

    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.CASCADE,
        related_name="reservas"
    )

    bodega = models.ForeignKey(
        "inventario.Bodega",
        on_delete=models.CASCADE,
        related_name="reservas"
    )

    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    documento_tipo = models.CharField(
        max_length=50,
        choices=TipoDocumentoReferencia.choices,
    )

    documento_id = models.UUIDField()

    class Meta:
        base_manager_name = "all_objects"