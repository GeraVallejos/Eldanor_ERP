from apps.productos.services.producto_trazabilidad_service import ProductoTrazabilidadService


class ProductoGobernanzaService:
    """Servicio de evaluacion de calidad y readiness del maestro de productos."""

    @staticmethod
    def evaluar_producto(*, empresa, producto):
        """Calcula score operativo y hallazgos clave para gobierno del maestro."""
        trazabilidad = ProductoTrazabilidadService.obtener_resumen(
            empresa=empresa,
            producto=producto,
        )
        hallazgos = []
        score = 100

        if not producto.categoria_id:
            hallazgos.append(
                {
                    "codigo": "GOB_SIN_CATEGORIA",
                    "dimension": "catalogo",
                    "nivel": "warning",
                    "detalle": "El producto no tiene categoria y pierde clasificacion operativa.",
                    "impacto": -15,
                }
            )
            score -= 15

        if not producto.impuesto_id:
            hallazgos.append(
                {
                    "codigo": "GOB_SIN_IMPUESTO",
                    "dimension": "compliance",
                    "nivel": "warning",
                    "detalle": "El producto no tiene impuesto asociado para documentos comerciales.",
                    "impacto": -15,
                }
            )
            score -= 15

        if producto.activo and trazabilidad["resumen"]["pedidos_venta"] > 0 and trazabilidad["resumen"]["listas_activas_vigentes"] == 0:
            hallazgos.append(
                {
                    "codigo": "GOB_SIN_PRECIO_VIGENTE",
                    "dimension": "ventas",
                    "nivel": "warning",
                    "detalle": "El producto tiene uso en ventas, pero no dispone de lista vigente.",
                    "impacto": -20,
                }
            )
            score -= 20

        if producto.maneja_inventario and not producto.stock_minimo:
            hallazgos.append(
                {
                    "codigo": "GOB_STOCK_MINIMO_NO_DEFINIDO",
                    "dimension": "inventario",
                    "nivel": "warning",
                    "detalle": "El producto inventariable no tiene stock minimo configurado.",
                    "impacto": -10,
                }
            )
            score -= 10

        if producto.tipo == "SERVICIO" and producto.maneja_inventario:
            hallazgos.append(
                {
                    "codigo": "GOB_SERVICIO_CON_INVENTARIO",
                    "dimension": "modelo",
                    "nivel": "critical",
                    "detalle": "El maestro presenta una combinacion inconsistente entre tipo y manejo de inventario.",
                    "impacto": -25,
                }
            )
            score -= 25

        score = max(score, 0)

        return {
            "producto_id": str(producto.id),
            "score": score,
            "estado": "LISTO" if score >= 85 else "OBSERVADO" if score >= 60 else "RIESGO",
            "readiness": {
                "ventas": bool(producto.impuesto_id and (trazabilidad["resumen"]["listas_activas_vigentes"] > 0 or trazabilidad["resumen"]["pedidos_venta"] == 0)),
                "inventario": bool((not producto.maneja_inventario) or producto.stock_minimo),
                "compliance": bool(producto.impuesto_id),
            },
            "hallazgos": hallazgos,
            "metricas": {
                "listas_vigentes": trazabilidad["resumen"]["listas_activas_vigentes"],
                "pedidos_venta": trazabilidad["resumen"]["pedidos_venta"],
                "documentos_compra": trazabilidad["resumen"]["documentos_compra"],
            },
        }
