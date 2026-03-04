from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel
from apps.presupuestos.models.presupuesto import EstadoPresupuesto, Presupuesto

class PresupuestoItem(BaseModel):

    presupuesto = models.ForeignKey(
        Presupuesto,
        on_delete=models.CASCADE,
        related_name="items"
    )

    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    descripcion = models.CharField(max_length=255)

    cantidad = models.DecimalField(max_digits=14, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=14, decimal_places=2)

    descuento = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    impuesto = models.ForeignKey(
        "productos.Impuesto",
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    impuesto_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def clean(self):
        super().clean()
        if self.producto and self.producto.empresa != self.presupuesto.empresa:
            raise ValidationError({"producto": "El producto no pertenece a la empresa del presupuesto."})


    def save(self, *args, **kwargs):

        if not self.descripcion and self.producto:
            self.descripcion = self.producto.nombre

        if not self.impuesto and self.producto:
            self.impuesto = self.producto.impuesto

        # Validaciones de Estado (Guardia de Negocio)
        # Verificamos si es edición (self.pk) o creación (else)
        if self.pk:
            if self.presupuesto.estado == EstadoPresupuesto.APROBADO:
                raise ValidationError("No se puede modificar un ítem de un presupuesto aprobado.")
        elif self.presupuesto.estado == EstadoPresupuesto.APROBADO:
             raise ValidationError("No se pueden añadir ítems a un presupuesto aprobado.")

        # Cálculos Automáticos (Trigger del CalculoService)
        # Importante: Importar CalculoService dentro del método para evitar importación circular
        from apps.presupuestos.services.calculo_service import CalculoService

        if self.impuesto and self.impuesto.empresa != self.presupuesto.empresa:
            raise ValidationError("El impuesto seleccionado no pertenece a esta empresa.")
        
        tasa = self.impuesto.porcentaje if self.impuesto else Decimal("0.00")
        self.impuesto_porcentaje = tasa

        # Obtenemos los cálculos exactos
        resultados = CalculoService.calcular_totales_item(
            cantidad=self.cantidad,
            precio_unitario=self.precio_unitario,
            porcentaje_descuento=self.descuento, # Asumiendo que 'descuento' es un %
            tasa_impuesto=tasa
        )
        
        # Asignamos valores calculados al objeto antes de guardar
        self.subtotal = resultados["subtotal"]
        self.total = resultados["total"]

        # Guardado en Base de Datos
        super().save(*args, **kwargs)

        # Actualización del Encabezado (Trigger de Recalculo)
        CalculoService.recalcular_presupuesto(self.presupuesto)

    def delete(self, *args, **kwargs):
        # Impedir borrar si está aprobado
        if self.presupuesto.estado == EstadoPresupuesto.APROBADO:
            raise ValidationError("No se puede eliminar un ítem de un presupuesto aprobado.")
        
        presupuesto_padre = self.presupuesto
        super().delete(*args, **kwargs)
        
        # Recalcular el presupuesto después de borrar el ítem
        from apps.presupuestos.services.calculo_service import CalculoService
        CalculoService.recalcular_presupuesto(presupuesto_padre)