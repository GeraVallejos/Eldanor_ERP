from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models.base import BaseModel
from apps.core.validators import formatear_rut, normalizar_texto, validar_rut_con_dv


class AmbienteTributario(models.TextChoices):
    CERTIFICACION = "CERTIFICACION", "Certificacion"
    PRODUCCION = "PRODUCCION", "Produccion"


class TipoDocumentoTributario(models.TextChoices):
    FACTURA_VENTA = "FACTURA_VENTA", "Factura de venta"
    GUIA_DESPACHO = "GUIA_DESPACHO", "Guia de despacho"
    NOTA_CREDITO_VENTA = "NOTA_CREDITO_VENTA", "Nota de credito de venta"


class ConfiguracionTributaria(BaseModel):
    """Configuracion tributaria operativa por empresa para integracion con SII."""

    ambiente = models.CharField(
        max_length=20,
        choices=AmbienteTributario.choices,
        default=AmbienteTributario.CERTIFICACION,
    )
    rut_emisor = models.CharField(max_length=12)
    razon_social = models.CharField(max_length=200)
    certificado_alias = models.CharField(max_length=150, blank=True)
    certificado_activo = models.BooleanField(default=False)
    resolucion_numero = models.PositiveIntegerField(null=True, blank=True)
    resolucion_fecha = models.DateField(null=True, blank=True)
    email_intercambio_dte = models.EmailField(blank=True)
    proveedor_envio = models.CharField(max_length=80, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        db_table = "facturacion_configuraciontributaria"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa"],
                name="unique_configuracion_tributaria_por_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "activa"], name="fac_cfg_emp_act_idx"),
        ]

    def clean(self):
        super().clean()
        self.rut_emisor = formatear_rut(self.rut_emisor)
        validar_rut_con_dv(self.rut_emisor)

        self.razon_social = normalizar_texto(self.razon_social)
        self.certificado_alias = normalizar_texto(self.certificado_alias)
        self.proveedor_envio = normalizar_texto(self.proveedor_envio)

        if self.activa and not self.certificado_activo:
            raise ValidationError(
                {"certificado_activo": "La configuracion activa requiere certificado digital operativo."}
            )

    def save(self, *args, **kwargs):
        self.rut_emisor = formatear_rut(self.rut_emisor)
        self.razon_social = normalizar_texto(self.razon_social)
        self.certificado_alias = normalizar_texto(self.certificado_alias)
        self.proveedor_envio = normalizar_texto(self.proveedor_envio)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.empresa} - {self.ambiente}"


class RangoFolioTributario(BaseModel):
    """Rango de folios autorizados por CAF para un tipo de DTE."""

    tipo_documento = models.CharField(
        max_length=40,
        choices=TipoDocumentoTributario.choices,
    )
    caf_nombre = models.CharField(max_length=120)
    folio_desde = models.PositiveIntegerField()
    folio_hasta = models.PositiveIntegerField()
    folio_actual = models.PositiveIntegerField(null=True, blank=True)
    fecha_autorizacion = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "facturacion_rangofoliotributario"
        indexes = [
            models.Index(fields=["empresa", "tipo_documento", "activo"], name="fac_rango_emp_tipo_act_idx"),
            models.Index(fields=["empresa", "fecha_vencimiento"], name="fac_rango_emp_venc_idx"),
        ]

    def clean(self):
        super().clean()
        self.caf_nombre = normalizar_texto(self.caf_nombre)

        if self.folio_hasta < self.folio_desde:
            raise ValidationError(
                {"folio_hasta": "El folio hasta no puede ser menor al folio desde."}
            )

        if self.folio_actual is not None:
            if self.folio_actual < self.folio_desde:
                raise ValidationError(
                    {"folio_actual": "El folio actual no puede quedar antes del inicio del rango."}
                )
            if self.folio_actual > self.folio_hasta:
                raise ValidationError(
                    {"folio_actual": "El folio actual no puede exceder el maximo autorizado."}
                )

        if self.fecha_vencimiento and self.fecha_autorizacion:
            if self.fecha_vencimiento < self.fecha_autorizacion:
                raise ValidationError(
                    {"fecha_vencimiento": "La vigencia no puede terminar antes de la autorizacion."}
                )

    def save(self, *args, **kwargs):
        self.caf_nombre = normalizar_texto(self.caf_nombre)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo_documento} {self.folio_desde}-{self.folio_hasta}"
