from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel


class ListaPrecio(BaseModel):
    """Lista de precios comercial con vigencia y alcance por cliente."""

    nombre = models.CharField(max_length=120)
    moneda = models.ForeignKey(
        "core.Moneda",
        on_delete=models.PROTECT,
        related_name="listas_precio",
    )
    cliente = models.ForeignKey(
        "contactos.Cliente",
        on_delete=models.CASCADE,
        related_name="listas_precio",
        null=True,
        blank=True,
    )
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    prioridad = models.PositiveSmallIntegerField(default=100)

    class Meta:
        indexes = [
            models.Index(fields=["empresa", "activa", "fecha_desde"]),
            models.Index(fields=["empresa", "cliente", "activa"]),
        ]

    def clean(self):
        super().clean()
        if self.fecha_hasta and self.fecha_hasta < self.fecha_desde:
            raise ValidationError({"fecha_hasta": "La fecha hasta no puede ser menor a fecha desde."})
        if self.moneda and self.moneda.empresa_id != self.empresa_id:
            raise ValidationError({"moneda": "La moneda no pertenece a la empresa activa."})
        if self.cliente and self.cliente.empresa_id != self.empresa_id:
            raise ValidationError({"cliente": "El cliente no pertenece a la empresa activa."})

    def __str__(self):
        return self.nombre


class ListaPrecioItem(BaseModel):
    """Precio por producto dentro de una lista comercial."""

    lista = models.ForeignKey(
        "productos.ListaPrecio",
        on_delete=models.CASCADE,
        related_name="items",
    )
    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        related_name="precios_lista",
    )
    precio = models.DecimalField(max_digits=14, decimal_places=2)
    descuento_maximo = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "lista", "producto"],
                name="uniq_lista_producto_empresa",
            )
        ]
        indexes = [models.Index(fields=["empresa", "producto"])]

    def clean(self):
        super().clean()
        if Decimal(self.precio or 0) < 0:
            raise ValidationError({"precio": "El precio no puede ser negativo."})
        if Decimal(self.descuento_maximo or 0) < 0 or Decimal(self.descuento_maximo or 0) > 100:
            raise ValidationError({"descuento_maximo": "El descuento maximo debe estar entre 0 y 100."})
        if self.lista and self.lista.empresa_id != self.empresa_id:
            raise ValidationError({"lista": "La lista no pertenece a la empresa activa."})
        if self.producto and self.producto.empresa_id != self.empresa_id:
            raise ValidationError({"producto": "El producto no pertenece a la empresa activa."})
