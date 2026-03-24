from datetime import date

from apps.compras.models import DocumentoCompraProveedorItem, EstadoDocumentoCompra
from apps.productos.models import ListaPrecioItem
from apps.ventas.models import EstadoPedidoVenta, PedidoVentaItem


class ProductoTrazabilidadService:
    """Servicio de lectura para consolidar trazabilidad comercial y alertas del maestro de productos."""

    PEDIDO_ESTADOS_RELEVANTES = {
        EstadoPedidoVenta.CONFIRMADO,
        EstadoPedidoVenta.EN_PROCESO,
        EstadoPedidoVenta.DESPACHADO,
        EstadoPedidoVenta.FACTURADO,
    }
    DOCUMENTO_COMPRA_ESTADOS_RELEVANTES = {
        EstadoDocumentoCompra.CONFIRMADO,
    }

    @staticmethod
    def _build_alertas(*, producto, listas_activas_vigentes, pedidos_count, compras_count):
        """Construye alertas funcionales del maestro para exponer riesgos de configuracion y uso."""
        alertas = []

        if not producto.categoria_id:
            alertas.append(
                {
                    "codigo": "SIN_CATEGORIA",
                    "nivel": "warning",
                    "detalle": "El producto no tiene categoria asignada.",
                }
            )

        if not producto.impuesto_id:
            alertas.append(
                {
                    "codigo": "SIN_IMPUESTO",
                    "nivel": "warning",
                    "detalle": "El producto no tiene impuesto configurado.",
                }
            )

        if producto.maneja_inventario and not producto.stock_minimo:
            alertas.append(
                {
                    "codigo": "SIN_STOCK_MINIMO",
                    "nivel": "warning",
                    "detalle": "El producto maneja inventario, pero no tiene stock minimo definido.",
                }
            )

        if producto.activo and pedidos_count > 0 and listas_activas_vigentes == 0:
            alertas.append(
                {
                    "codigo": "SIN_LISTA_VIGENTE",
                    "nivel": "info",
                    "detalle": "El producto ya se usa en ventas, pero hoy no tiene listas de precio vigentes configuradas.",
                }
            )

        if not producto.activo and (pedidos_count > 0 or compras_count > 0):
            alertas.append(
                {
                    "codigo": "PRODUCTO_INACTIVO_CON_HISTORIAL",
                    "nivel": "info",
                    "detalle": "El producto esta inactivo y conserva historial comercial para trazabilidad.",
                }
            )

        return alertas

    @staticmethod
    def obtener_resumen(*, empresa, producto, fecha=None):
        """Consolida listas de precio, referencias documentales y alertas operativas del producto."""
        fecha = fecha or date.today()

        listas_qs = (
            ListaPrecioItem.all_objects.filter(empresa=empresa, producto=producto)
            .select_related("lista__moneda", "lista__cliente__contacto")
            .order_by("lista__prioridad", "lista__nombre")
        )
        listas = []
        listas_activas_vigentes = 0
        for item in listas_qs:
            lista = item.lista
            esta_vigente = bool(
                lista.activa
                and lista.fecha_desde <= fecha
                and (lista.fecha_hasta is None or lista.fecha_hasta >= fecha)
            )
            if esta_vigente:
                listas_activas_vigentes += 1
            listas.append(
                {
                    "id": str(lista.id),
                    "nombre": lista.nombre,
                    "cliente_nombre": getattr(getattr(lista.cliente, "contacto", None), "nombre", None),
                    "moneda_codigo": getattr(lista.moneda, "codigo", None),
                    "precio": item.precio,
                    "descuento_maximo": item.descuento_maximo,
                    "fecha_desde": lista.fecha_desde,
                    "fecha_hasta": lista.fecha_hasta,
                    "activa": lista.activa,
                    "prioridad": lista.prioridad,
                    "esta_vigente": esta_vigente,
                }
            )

        pedidos_qs = (
            PedidoVentaItem.objects.filter(empresa=empresa, producto=producto)
            .select_related("pedido_venta__cliente__contacto", "pedido_venta__lista_precio")
            .filter(pedido_venta__estado__in=ProductoTrazabilidadService.PEDIDO_ESTADOS_RELEVANTES)
            .order_by("-pedido_venta__fecha_emision", "-pedido_venta__creado_en")
        )
        pedidos_count = pedidos_qs.count()
        pedidos = [
            {
                "id": str(item.pedido_venta.id),
                "numero": item.pedido_venta.numero,
                "estado": item.pedido_venta.estado,
                "fecha_emision": item.pedido_venta.fecha_emision,
                "cliente_nombre": getattr(item.pedido_venta.cliente.contacto, "nombre", None),
                "lista_precio_nombre": getattr(item.pedido_venta.lista_precio, "nombre", None),
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
            }
            for item in pedidos_qs[:5]
        ]

        compras_qs = (
            DocumentoCompraProveedorItem.objects.filter(empresa=empresa, producto=producto)
            .select_related("documento__proveedor__contacto")
            .filter(documento__estado__in=ProductoTrazabilidadService.DOCUMENTO_COMPRA_ESTADOS_RELEVANTES)
            .order_by("-documento__fecha_emision", "-documento__creado_en")
        )
        compras_count = compras_qs.count()
        compras = [
            {
                "id": str(item.documento.id),
                "tipo_documento": item.documento.tipo_documento,
                "folio": item.documento.folio,
                "estado": item.documento.estado,
                "fecha_emision": item.documento.fecha_emision,
                "proveedor_nombre": getattr(item.documento.proveedor.contacto, "nombre", None),
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
            }
            for item in compras_qs[:5]
        ]

        return {
            "producto_id": str(producto.id),
            "fecha_referencia": fecha,
            "resumen": {
                "listas_configuradas": len(listas),
                "listas_activas_vigentes": listas_activas_vigentes,
                "pedidos_venta": pedidos_count,
                "documentos_compra": compras_count,
            },
            "listas_precio": listas,
            "uso_documentos": {
                "pedidos_venta": {
                    "cantidad": pedidos_count,
                    "ultimos": pedidos,
                },
                "documentos_compra": {
                    "cantidad": compras_count,
                    "ultimos": compras,
                },
            },
            "alertas": ProductoTrazabilidadService._build_alertas(
                producto=producto,
                listas_activas_vigentes=listas_activas_vigentes,
                pedidos_count=pedidos_count,
                compras_count=compras_count,
            ),
        }
