from django.db import models
from django.conf import settings

from apps.contactos.models import Proveedor
from apps.core.models import BaseModel


class TipoDocumentoCompra(models.TextChoices):
    GUIA_RECEPCION = "GUIA_RECEPCION", "Guía de recepción"
    FACTURA_COMPRA = "FACTURA_COMPRA", "Factura de compra"


class EstadoDocumentoCompra(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    CONFIRMADO = "CONFIRMADO", "Confirmado"
    ANULADO = "ANULADO", "Anulado"


class DocumentoCompraProveedor(BaseModel):

    tipo_documento = models.CharField(
        max_length=20,
        choices=TipoDocumentoCompra.choices,
    )

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="documentos_compra",
    )

    folio = models.CharField(max_length=50)
    serie = models.CharField(max_length=10, blank=True)

    fecha_emision = models.DateField()
    fecha_recepcion = models.DateField()

    subtotal_neto = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    moneda = models.ForeignKey(
        "core.Moneda",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="documentos_compra",
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoDocumentoCompra.choices,
        default=EstadoDocumentoCompra.BORRADOR,
    )

    observaciones = models.TextField(blank=True)

    # UUID del documento original del proveedor (SII, ERP externo, etc.) para idempotencia
    uuid_externo = models.UUIDField(null=True, blank=True)

    orden_compra = models.ForeignKey(
        "compras.OrdenCompra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_compra",
    )

    recepcion_compra = models.ForeignKey(
        "compras.RecepcionCompra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_compra",
    )

    documento_origen = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_correccion",
    )

    motivo_correccion = models.TextField(blank=True)

    corregido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_compra_corregidos",
    )

    corregido_en = models.DateTimeField(null=True, blank=True)

    # Flag técnico para unicidad compatible con MySQL (sin constraints condicionales).
    bloquea_duplicado = models.BooleanField(default=True, editable=False)

    # Auditoría de ciclo de vida
    confirmado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_compra_confirmados",
    )
    confirmado_en = models.DateTimeField(null=True, blank=True)

    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_compra_anulados",
    )
    anulado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "uuid_externo"],
                name="unique_uuid_externo_por_empresa",
            ),
            models.UniqueConstraint(
                fields=["empresa", "proveedor", "tipo_documento", "folio", "serie", "bloquea_duplicado"],
                name="uniq_doc_compra_emp_prov_tipo_folio_serie_activo",
            ),
        ]
        indexes = [
            models.Index(fields=["empresa", "proveedor"]),
            models.Index(fields=["empresa", "tipo_documento", "estado"]),
            models.Index(fields=["empresa", "moneda"]),
            models.Index(fields=["empresa", "documento_origen"]),
        ]

    def __str__(self):
        return f"{self.get_tipo_documento_display()} {self.folio}"
