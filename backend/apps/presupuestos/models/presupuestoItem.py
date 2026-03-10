from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.core.mixins import TenantRelationValidationMixin
from apps.documentos.models import DocumentoItemBase
from apps.presupuestos.models.presupuesto import EstadoPresupuesto, Presupuesto


class PresupuestoItem(TenantRelationValidationMixin, DocumentoItemBase):
    tenant_fk_fields = ["presupuesto", "producto", "impuesto"]

    presupuesto = models.ForeignKey(
        Presupuesto,
        on_delete=models.CASCADE,
        related_name="items",
    )

    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    cantidad = models.DecimalField(max_digits=14, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=14, decimal_places=2)

    descuento = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    impuesto_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        base_manager_name = "all_objects"

    @transaction.atomic
    def save(self, *args, **kwargs):
        if not self.descripcion and self.producto:
            self.descripcion = self.producto.nombre

        if not self.impuesto and self.producto:
            self.impuesto = self.producto.impuesto

        # Guardia de negocio por estado del presupuesto.
        if self.pk:
            if self.presupuesto.estado == EstadoPresupuesto.APROBADO:
                raise ValidationError("No se puede modificar un item de un presupuesto aprobado.")
        elif self.presupuesto.estado == EstadoPresupuesto.APROBADO:
            raise ValidationError("No se pueden anadir items a un presupuesto aprobado.")

        from apps.presupuestos.services.calculo_service import CalculoService

        if self.impuesto and self.impuesto.empresa != self.presupuesto.empresa:
            raise ValidationError("El impuesto seleccionado no pertenece a esta empresa.")

        # En item, descuento se interpreta como porcentaje.
        if self.descuento < 0 or self.descuento > 100:
            raise ValidationError({"descuento": "El descuento del item debe estar entre 0 y 100."})

        tasa = self.impuesto.porcentaje if self.impuesto else Decimal("0.00")
        self.impuesto_porcentaje = tasa

        resultados = CalculoService.calcular_totales_item(
            cantidad=self.cantidad,
            precio_unitario=self.precio_unitario,
            porcentaje_descuento=self.descuento,
            tasa_impuesto=tasa,
        )

        self.subtotal = resultados["subtotal"]
        self.total = resultados["total"]

        super().save(*args, **kwargs)

        CalculoService.recalcular_presupuesto(self.presupuesto)

    def delete(self, *args, **kwargs):
        if self.presupuesto.estado == EstadoPresupuesto.APROBADO:
            raise ValidationError("No se puede eliminar un item de un presupuesto aprobado.")

        presupuesto_padre = self.presupuesto
        super().delete(*args, **kwargs)

        from apps.presupuestos.services.calculo_service import CalculoService

        CalculoService.recalcular_presupuesto(presupuesto_padre)
