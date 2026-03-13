from datetime import date

from django.db import models

from apps.core.services import TipoCambioService
from apps.productos.models import ListaPrecio, ListaPrecioItem


class PrecioComercialService:
    """Servicio de resolucion de precio para ventas y cotizaciones."""

    @staticmethod
    def _resolver_lista(*, empresa, cliente=None, fecha=None):
        fecha = fecha or date.today()

        queryset = ListaPrecio.all_objects.filter(
            empresa=empresa,
            activa=True,
            fecha_desde__lte=fecha,
        ).filter(
            models.Q(fecha_hasta__isnull=True) | models.Q(fecha_hasta__gte=fecha)
        )

        if cliente:
            lista_cliente = (
                queryset.filter(cliente=cliente)
                .order_by("prioridad", "-fecha_desde", "-creado_en")
                .first()
            )
            if lista_cliente:
                return lista_cliente

        return queryset.filter(cliente__isnull=True).order_by("prioridad", "-fecha_desde", "-creado_en").first()

    @staticmethod
    def obtener_precio(*, empresa, producto, cliente=None, fecha=None, moneda_destino=None):
        """Resuelve precio comercial priorizando lista cliente y fallback a referencia."""
        fecha = fecha or date.today()
        lista = PrecioComercialService._resolver_lista(empresa=empresa, cliente=cliente, fecha=fecha)

        if lista:
            item = ListaPrecioItem.all_objects.filter(
                empresa=empresa,
                lista=lista,
                producto=producto,
            ).first()
            if item:
                monto = item.precio
                moneda_origen = lista.moneda
                fuente = "LISTA_PRECIO"
            else:
                monto = producto.precio_referencia
                moneda_origen = producto.moneda
                fuente = "PRODUCTO_REFERENCIA"
        else:
            monto = producto.precio_referencia
            moneda_origen = producto.moneda
            fuente = "PRODUCTO_REFERENCIA"

        if moneda_destino and moneda_origen and moneda_destino.id != moneda_origen.id:
            monto = TipoCambioService.convertir_monto(
                empresa=empresa,
                monto=monto,
                moneda_origen=moneda_origen,
                moneda_destino=moneda_destino,
                fecha=fecha,
                decimales=2,
            )
            moneda_resuelta = moneda_destino
        else:
            moneda_resuelta = moneda_origen

        return {
            "precio": monto,
            "moneda": moneda_resuelta,
            "fuente": fuente,
            "lista": lista,
        }
