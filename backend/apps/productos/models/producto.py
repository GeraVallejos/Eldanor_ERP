from django.db import models
from apps.core.models import BaseModel
from apps.core.tenant import get_current_empresa
from apps.productos.services.producto_validation import clean_producto
from apps.productos.validators import normalize_sku
from apps.core.validators import normalizar_texto
from apps.core.mixins import TenantRelationValidationMixin


class TipoProducto(models.TextChoices):
    PRODUCTO = "PRODUCTO", "Producto"
    SERVICIO = "SERVICIO", "Servicio"


class UnidadMedida(models.TextChoices):
    UNIDAD = "UN", "Unidad"
    KILOGRAMO = "KG", "Kilogramo"
    GRAMO = "GR", "Gramo"
    LITRO = "LT", "Litro"
    METRO = "MT", "Metro"
    METRO_CUADRADO = "M2", "Metro Cuadrado"
    METRO_CUBICO = "M3", "Metro Cubico"
    CAJA = "CJ", "Caja"


class Producto(TenantRelationValidationMixin, BaseModel):

    tenant_fk_fields = ["categoria", "impuesto", "moneda"]

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

    moneda = models.ForeignKey(
        "tesoreria.Moneda",
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

    unidad_medida = models.CharField(
        max_length=10,
        choices=UnidadMedida.choices,
        default=UnidadMedida.UNIDAD,
    )

    permite_decimales = models.BooleanField(default=True)

    maneja_inventario = models.BooleanField(default=True)

    stock_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    costo_promedio = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=0
    )

    stock_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    usa_lotes = models.BooleanField(default=False)

    usa_series = models.BooleanField(default=False)

    usa_vencimiento = models.BooleanField(default=False)

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

        if not self.empresa_id:
            empresa_contexto = get_current_empresa()
            if empresa_contexto:
                self.empresa = empresa_contexto

        if self.empresa_id and not self.moneda_id:
            from apps.tesoreria.models import Moneda

            self.moneda = Moneda.all_objects.filter(
                empresa_id=self.empresa_id,
                es_base=True,
                activa=True,
            ).first()

        # Regla estructural antes de validar
        if self.tipo == TipoProducto.SERVICIO:
            self.maneja_inventario = False
            self.stock_actual = 0
            self.costo_promedio = 0
            self.stock_minimo = 0
            self.usa_lotes = False
            self.usa_series = False
            self.usa_vencimiento = False

        if not self.maneja_inventario:
            self.stock_actual = 0
            self.stock_minimo = 0
            self.usa_lotes = False
            self.usa_series = False
            self.usa_vencimiento = False

        if self.usa_series:
            self.usa_lotes = True
            self.permite_decimales = False

        super().save(*args, **kwargs)

        if self.empresa_id and not self.moneda_id:
            from apps.tesoreria.models import Moneda

            moneda_base = Moneda.all_objects.filter(
                empresa_id=self.empresa_id,
                es_base=True,
                activa=True,
            ).first()
            if moneda_base:
                self.__class__.all_objects.filter(pk=self.pk, moneda__isnull=True).update(moneda=moneda_base)
                self.moneda = moneda_base

    

    def __str__(self):
        return f"{self.nombre} ({self.sku})"
    
