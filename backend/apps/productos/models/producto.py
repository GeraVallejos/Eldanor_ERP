from django.db import models
from apps.core.models import BaseModel
from apps.productos.services.producto_validation import clean_producto
from apps.productos.validators import normalize_sku
from apps.core.validators import normalizar_texto
from apps.core.mixins import TenantRelationValidationMixin


class TipoProducto(models.TextChoices):
    PRODUCTO = "PRODUCTO", "Producto"
    SERVICIO = "SERVICIO", "Servicio"


class Producto(TenantRelationValidationMixin, BaseModel):

    tenant_fk_fields = ["categoria", "impuesto"]

    nombre = models.CharField(max_length=255)

    descripcion = models.TextField(blank=True)

    sku = models.CharField(
        max_length=100,
        help_text="Código interno del producto"
    )

    tipo = models.CharField(
        max_length=20,
        choices=TipoProducto.choices,
        default=TipoProducto.PRODUCTO
    )

    categoria = models.ForeignKey(
        "productos.Categoria",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="productos"
    )

    impuesto = models.ForeignKey(
        "productos.Impuesto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="productos"
    )

    precio_referencia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Precio sugerido o referencia"
    )

    precio_costo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    maneja_inventario = models.BooleanField(default=True)

    stock_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            # Regla 1: No repetir nombre en la misma empresa  
            models.UniqueConstraint(
                fields=['empresa', 'nombre'], 
                name='unique_nombre_producto_por_empresa'
            ),
            # Regla 2: No repetir SKU en la misma empresa
            models.UniqueConstraint(
                fields=['empresa', 'sku'], 
                name='unique_sku_producto_por_empresa'
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "nombre"]),
            models.Index(fields=["empresa", "sku"]),
        ]


    def clean(self):
        super().clean() 
        clean_producto(self)  

    def save(self, *args, **kwargs):
        self.nombre = normalizar_texto(self.nombre)
        self.descripcion = normalizar_texto(self.descripcion)
        # Normalizacion de SKU
        if self.sku:
            self.sku = normalize_sku(self.sku)

        # Regla estructural antes de validar
        if self.tipo == TipoProducto.SERVICIO:
            self.maneja_inventario = False
            self.stock_actual = 0

        super().save(*args, **kwargs)

    

    def __str__(self):
        return f"{self.nombre} ({self.sku})"
    