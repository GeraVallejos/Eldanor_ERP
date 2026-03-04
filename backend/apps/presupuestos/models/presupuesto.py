from django.db import models
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel
from apps.core.mixins import AuditDiffMixin


class EstadoPresupuesto(models.TextChoices):
    BORRADOR = "BORRADOR", "Borrador"
    ENVIADO = "ENVIADO", "Enviado"
    APROBADO = "APROBADO", "Aprobado"
    RECHAZADO = "RECHAZADO", "Rechazado"
    ANULADO = "ANULADO", "Anulado"


class Presupuesto(AuditDiffMixin, BaseModel):

    numero = models.PositiveIntegerField()

    cliente = models.ForeignKey(
        "contactos.Cliente",
        on_delete=models.PROTECT,
        related_name="presupuestos"
    )

    fecha = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)

    estado = models.CharField(
        max_length=20,
        choices=EstadoPresupuesto.choices,
        default=EstadoPresupuesto.BORRADOR
    )

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    impuesto_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha"]


    def save(self, *args, **kwargs):
        # 1. Solo buscar el 'original' si el objeto YA tiene un ID (es una edición)
        if self.pk:
            try:
                original = Presupuesto.all_objects.get(pk=self.pk)
                
                # Guardia: Impedir cambios si ya está aprobado
                if original.estado == EstadoPresupuesto.APROBADO and self.estado == EstadoPresupuesto.APROBADO:
                    raise ValidationError(
                        "No se puede modificar un presupuesto ya aprobado. "
                        "Para realizar cambios, anule este y clone uno nuevo."
                    )
            except Presupuesto.DoesNotExist:
                # Si por alguna razón tiene PK pero no está en DB (raro pero posible en tests)
                pass
        
        # 2. Lógica para fechas automáticas
        if not self.fecha_vencimiento and self.fecha:
            from datetime import timedelta
            # Aseguramos que sea objeto date si viene como string
            if isinstance(self.fecha, str):
                from django.utils.dateparse import parse_date
                fecha_dt = parse_date(self.fecha)
            else:
                fecha_dt = self.fecha
                
            if fecha_dt:
                self.fecha_vencimiento = fecha_dt + timedelta(days=15)

        # 3. Guardado real
        super().save(*args, **kwargs)

    
    def clean(self):
        # Llamar al clean del padre si existe
        super().clean()

        # Validar que el cliente pertenezca a la misma empresa que el presupuesto
        if self.cliente and self.cliente.empresa != self.empresa:
            raise ValidationError({"cliente": "El cliente seleccionado no pertenece a esta empresa."})

        # Validación de fechas
        if self.fecha and self.fecha_vencimiento:
            if self.fecha_vencimiento < self.fecha:
                raise ValidationError({
                    'fecha_vencimiento': "La fecha de vencimiento no puede ser anterior a la fecha de emisión."
                })


    def __str__(self):
        return f"{self.numero} - {self.cliente}"