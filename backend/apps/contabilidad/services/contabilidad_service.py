from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.contabilidad.models import (
    AsientoContable,
    ClaveCuentaContable,
    ConfiguracionCuentaContable,
    EstadoAsientoContable,
    MovimientoContable,
    OrigenAsientoContable,
    PlanCuenta,
    TipoCuentaContable,
)
from apps.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from apps.core.models import OutboxEvent, OutboxStatus, TipoDocumento
from apps.core.services import DomainEventService, OutboxService, SecuenciaService
from apps.documentos.models import EstadoContable


class ContabilidadService:
    """Gestiona plan de cuentas, asientos y procesamiento de solicitudes contables."""

    CODIGOS_BASE = {
        "CAJA": ("111100", "Caja", TipoCuentaContable.ACTIVO),
        "BANCO": ("111200", "Bancos", TipoCuentaContable.ACTIVO),
        "CLIENTES": ("112100", "Clientes", TipoCuentaContable.ACTIVO),
        "IVA_CREDITO": ("119200", "IVA Credito Fiscal", TipoCuentaContable.ACTIVO),
        "PROVEEDORES": ("211100", "Proveedores", TipoCuentaContable.PASIVO),
        "IVA_DEBITO": ("213100", "IVA Debito Fiscal", TipoCuentaContable.PASIVO),
        "CAPITAL": ("311100", "Capital", TipoCuentaContable.PATRIMONIO),
        "VENTAS": ("411100", "Ventas", TipoCuentaContable.INGRESO),
        "COMPRAS": ("511100", "Compras y Servicios", TipoCuentaContable.GASTO),
    }

    @staticmethod
    def _decimal(value):
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))

    @staticmethod
    def recalcular_totales(*, asiento):
        """Recalcula totales y marca si el asiento queda cuadrado."""
        movimientos = MovimientoContable.all_objects.filter(empresa=asiento.empresa, asiento=asiento)
        total_debe = sum((ContabilidadService._decimal(mov.debe) for mov in movimientos), Decimal("0.00"))
        total_haber = sum((ContabilidadService._decimal(mov.haber) for mov in movimientos), Decimal("0.00"))
        cuadrado = total_debe == total_haber and total_debe > 0

        AsientoContable.all_objects.filter(id=asiento.id).update(
            total_debe=total_debe,
            total_haber=total_haber,
            cuadrado=cuadrado,
        )
        asiento.total_debe = total_debe
        asiento.total_haber = total_haber
        asiento.cuadrado = cuadrado
        return asiento

    @staticmethod
    def validar_editable(*, asiento):
        """Valida que el asiento siga en borrador antes de aceptar cambios manuales."""
        if asiento.estado != EstadoAsientoContable.BORRADOR:
            raise ConflictError("Solo se puede modificar un asiento en estado BORRADOR.")

    @staticmethod
    @transaction.atomic
    def seed_plan_base(*, empresa, usuario=None):
        """Crea el plan minimo recomendado para iniciar la operacion contable."""
        creadas = []
        for _alias, (codigo, nombre, tipo) in ContabilidadService.CODIGOS_BASE.items():
            cuenta, created = PlanCuenta.all_objects.get_or_create(
                empresa=empresa,
                codigo=codigo,
                defaults={
                    "creado_por": usuario,
                    "nombre": nombre,
                    "tipo": tipo,
                    "acepta_movimientos": True,
                    "activa": True,
                },
            )
            if created:
                creadas.append(cuenta)
        ContabilidadService.seed_configuracion_base(empresa=empresa, usuario=usuario)
        return creadas

    @staticmethod
    @transaction.atomic
    def seed_configuracion_base(*, empresa, usuario=None):
        """Sincroniza configuraciones funcionales de cuentas usando el plan base actual."""
        creadas = []
        for clave in ClaveCuentaContable.values:
            codigo = ContabilidadService.CODIGOS_BASE.get(clave, ("", "", ""))[0]
            if not codigo:
                continue
            cuenta = PlanCuenta.all_objects.filter(empresa=empresa, codigo=codigo, activa=True).first()
            if not cuenta:
                continue
            config, created = ConfiguracionCuentaContable.all_objects.get_or_create(
                empresa=empresa,
                clave=clave,
                defaults={
                    "creado_por": usuario,
                    "cuenta": cuenta,
                    "descripcion": f"Configuracion base para {clave.lower()}",
                    "activa": True,
                },
            )
            if created:
                creadas.append(config)
        return creadas

    @staticmethod
    @transaction.atomic
    def crear_asiento(
        *,
        empresa,
        fecha,
        glosa,
        movimientos_data,
        usuario=None,
        referencia_tipo="",
        referencia_id=None,
        origen=OrigenAsientoContable.MANUAL,
    ):
        """Crea un asiento contable con sus lineas y recalcula su cuadratura."""
        if not movimientos_data:
            raise BusinessRuleError("El asiento debe tener al menos una linea contable.")

        numero = SecuenciaService.obtener_siguiente_numero(empresa, TipoDocumento.ASIENTO_CONTABLE)
        asiento = AsientoContable.all_objects.create(
            empresa=empresa,
            creado_por=usuario,
            numero=numero,
            fecha=fecha,
            glosa=glosa,
            referencia_tipo=referencia_tipo or "",
            referencia_id=referencia_id,
            origen=origen,
        )

        for movimiento in movimientos_data:
            cuenta = movimiento["cuenta"]
            MovimientoContable.all_objects.create(
                empresa=empresa,
                creado_por=usuario,
                asiento=asiento,
                cuenta=cuenta,
                glosa=movimiento.get("glosa") or glosa,
                debe=ContabilidadService._decimal(movimiento.get("debe")),
                haber=ContabilidadService._decimal(movimiento.get("haber")),
            )

        ContabilidadService.recalcular_totales(asiento=asiento)
        return asiento

    @staticmethod
    @transaction.atomic
    def contabilizar_asiento(*, asiento_id, empresa, usuario=None):
        """Contabiliza un asiento cuadrado y publica sus eventos de integracion."""
        asiento = AsientoContable.all_objects.select_for_update().filter(id=asiento_id, empresa=empresa).first()
        if not asiento:
            raise ResourceNotFoundError("Asiento contable no encontrado.")

        ContabilidadService.validar_editable(asiento=asiento)
        ContabilidadService.recalcular_totales(asiento=asiento)
        if not asiento.cuadrado:
            raise BusinessRuleError("No se puede contabilizar un asiento descuadrado.")

        asiento.estado = EstadoAsientoContable.CONTABILIZADO
        asiento.save(update_fields=["estado", "actualizado_en"])

        dedup_key = f"asiento:{asiento.id}:contabilizado"
        payload = {
            "asiento_id": str(asiento.id),
            "numero": asiento.numero,
            "fecha": str(asiento.fecha),
            "total_debe": str(asiento.total_debe),
            "total_haber": str(asiento.total_haber),
        }
        DomainEventService.record_event(
            empresa=empresa,
            aggregate_type="AsientoContable",
            aggregate_id=asiento.id,
            event_type="contabilidad.asiento_contabilizado",
            payload=payload,
            meta={"source": "ContabilidadService"},
            idempotency_key=dedup_key,
            usuario=usuario,
        )
        OutboxService.enqueue(
            empresa=empresa,
            topic="contabilidad.asiento",
            event_name="asiento.contabilizado",
            payload=payload,
            usuario=usuario,
            dedup_key=dedup_key,
        )
        return asiento

    @staticmethod
    @transaction.atomic
    def anular_asiento(*, asiento_id, empresa, usuario=None):
        """Anula un asiento contabilizado preservando su trazabilidad historica."""
        asiento = AsientoContable.all_objects.select_for_update().filter(id=asiento_id, empresa=empresa).first()
        if not asiento:
            raise ResourceNotFoundError("Asiento contable no encontrado.")
        if asiento.estado == EstadoAsientoContable.ANULADO:
            return asiento
        if asiento.estado != EstadoAsientoContable.CONTABILIZADO:
            raise ConflictError("Solo se pueden anular asientos ya contabilizados.")

        asiento.estado = EstadoAsientoContable.ANULADO
        asiento.save(update_fields=["estado", "actualizado_en"])
        return asiento

    @staticmethod
    def _buscar_cuenta_por_codigo(*, empresa, codigo):
        cuenta = PlanCuenta.all_objects.filter(empresa=empresa, codigo=str(codigo).strip().upper(), activa=True).first()
        if not cuenta:
            raise BusinessRuleError(
                f"No existe la cuenta contable {codigo} para la empresa activa.",
                error_code="ACCOUNTING_ACCOUNT_MISSING",
            )
        return cuenta

    @staticmethod
    def _buscar_cuenta_por_clave(*, empresa, clave):
        """Resuelve la cuenta contable desde una clave funcional parametrizable."""
        clave = str(clave or "").strip().upper()
        config = ConfiguracionCuentaContable.all_objects.filter(
            empresa=empresa,
            clave=clave,
            activa=True,
            cuenta__activa=True,
        ).select_related("cuenta").first()
        if config:
            return config.cuenta

        codigo = ContabilidadService.CODIGOS_BASE.get(clave, ("", "", ""))[0]
        if not codigo:
            raise BusinessRuleError(
                f"No existe configuracion contable para la clave {clave}.",
                error_code="ACCOUNTING_CONFIG_KEY_MISSING",
            )
        return ContabilidadService._buscar_cuenta_por_codigo(empresa=empresa, codigo=codigo)

    @staticmethod
    def _resolver_cuenta_linea(*, empresa, linea):
        """Resuelve la cuenta objetivo desde cuenta directa, codigo o clave funcional."""
        cuenta = linea.get("cuenta")
        if cuenta:
            return cuenta
        if linea.get("cuenta_codigo"):
            return ContabilidadService._buscar_cuenta_por_codigo(
                empresa=empresa,
                codigo=linea.get("cuenta_codigo"),
            )
        if linea.get("cuenta_clave"):
            return ContabilidadService._buscar_cuenta_por_clave(
                empresa=empresa,
                clave=linea.get("cuenta_clave"),
            )
        raise BusinessRuleError(
            "La linea contable no informa cuenta, codigo ni clave funcional.",
            error_code="ACCOUNTING_LINE_ACCOUNT_REQUIRED",
        )

    @staticmethod
    def _marcar_origen_contabilizado(*, aggregate_type, aggregate_id):
        """Actualiza el estado contable del documento origen cuando la centralizacion finaliza bien."""
        model_map = {
            "FacturaVenta": ("apps.ventas.models", "FacturaVenta"),
            "NotaCreditoVenta": ("apps.ventas.models", "NotaCreditoVenta"),
            "DocumentoCompraProveedor": ("apps.compras.models", "DocumentoCompraProveedor"),
            "MovimientoBancario": ("apps.core.models", "MovimientoBancario"),
        }
        mapping = model_map.get(aggregate_type)
        if not mapping:
            return

        module_name, model_name = mapping
        module = __import__(module_name, fromlist=[model_name])
        model = getattr(module, model_name)
        model.all_objects.filter(id=aggregate_id).update(
            estado_contable=EstadoContable.CONTABILIZADO,
        )

    @staticmethod
    def _marcar_origen_error(*, aggregate_type, aggregate_id):
        """Marca error contable sobre el documento origen cuando falla la centralizacion."""
        model_map = {
            "FacturaVenta": ("apps.ventas.models", "FacturaVenta"),
            "NotaCreditoVenta": ("apps.ventas.models", "NotaCreditoVenta"),
            "DocumentoCompraProveedor": ("apps.compras.models", "DocumentoCompraProveedor"),
            "MovimientoBancario": ("apps.core.models", "MovimientoBancario"),
        }
        mapping = model_map.get(aggregate_type)
        if not mapping:
            return

        module_name, model_name = mapping
        module = __import__(module_name, fromlist=[model_name])
        model = getattr(module, model_name)
        model.all_objects.filter(id=aggregate_id).update(
            estado_contable=EstadoContable.ERROR,
        )

    @staticmethod
    @transaction.atomic
    def generar_reversa_asiento(*, asiento_id, empresa, usuario=None, motivo=""):
        """Genera un contra-asiento contabilizado a partir de un asiento contabilizado."""
        asiento = (
            AsientoContable.all_objects
            .select_for_update()
            .filter(id=asiento_id, empresa=empresa)
            .first()
        )
        if not asiento:
            raise ResourceNotFoundError("Asiento contable no encontrado.")
        if asiento.estado != EstadoAsientoContable.CONTABILIZADO:
            raise ConflictError("Solo se puede revertir un asiento ya contabilizado.")

        ya_revertido = AsientoContable.all_objects.filter(
            empresa=empresa,
            referencia_tipo="REVERSA_ASIENTO",
            referencia_id=asiento.id,
        ).exists()
        if ya_revertido:
            raise ConflictError("El asiento ya tiene una reversa registrada.")

        movimientos_data = []
        for movimiento in asiento.movimientos.all():
            movimientos_data.append(
                {
                    "cuenta": movimiento.cuenta,
                    "glosa": movimiento.glosa or asiento.glosa,
                    "debe": movimiento.haber,
                    "haber": movimiento.debe,
                }
            )

        reversa = ContabilidadService.crear_asiento(
            empresa=empresa,
            fecha=timezone.localdate(),
            glosa=f"Reversa de {asiento.numero}: {motivo or asiento.glosa}",
            movimientos_data=movimientos_data,
            usuario=usuario,
            referencia_tipo="REVERSA_ASIENTO",
            referencia_id=asiento.id,
            origen=OrigenAsientoContable.INTEGRACION,
        )
        return ContabilidadService.contabilizar_asiento(
            asiento_id=reversa.id,
            empresa=empresa,
            usuario=usuario,
        )

    @staticmethod
    def listar_eventos_fallidos(*, empresa):
        """Obtiene eventos contables fallidos para analisis y reproceso."""
        return list(
            OutboxEvent.all_objects.filter(
                empresa=empresa,
                topic="contabilidad",
                event_name="ASIENTO_SOLICITADO",
                status=OutboxStatus.FAILED,
            ).order_by("-actualizado_en", "-creado_en")
        )

    @staticmethod
    @transaction.atomic
    def reprocesar_solicitudes_fallidas(*, empresa, usuario=None, limit=50):
        """Reencola solicitudes contables fallidas y las procesa nuevamente."""
        eventos = list(
            OutboxEvent.all_objects
            .select_for_update(skip_locked=True)
            .filter(
                empresa=empresa,
                topic="contabilidad",
                event_name="ASIENTO_SOLICITADO",
                status=OutboxStatus.FAILED,
            )
            .order_by("available_at", "creado_en")[:limit]
        )
        for event in eventos:
            event.status = OutboxStatus.PENDING
            event.last_error = ""
            event.save(update_fields=["status", "last_error", "actualizado_en"])
        return ContabilidadService.procesar_solicitudes_pendientes(
            empresa=empresa,
            usuario=usuario,
            limit=limit,
        )

    @staticmethod
    def reporte_libro_mayor(*, empresa, fecha_desde=None, fecha_hasta=None):
        """Construye libro mayor resumido por cuenta dentro de un rango de fechas."""
        movimientos = MovimientoContable.all_objects.select_related("asiento", "cuenta").filter(
            empresa=empresa,
            asiento__estado=EstadoAsientoContable.CONTABILIZADO,
        )
        if fecha_desde:
            movimientos = movimientos.filter(asiento__fecha__gte=fecha_desde)
        if fecha_hasta:
            movimientos = movimientos.filter(asiento__fecha__lte=fecha_hasta)

        mayor = {}
        for movimiento in movimientos.order_by("cuenta__codigo", "asiento__fecha", "creado_en"):
            clave = str(movimiento.cuenta_id)
            bucket = mayor.setdefault(
                clave,
                {
                    "cuenta_id": str(movimiento.cuenta_id),
                    "codigo": movimiento.cuenta.codigo,
                    "nombre": movimiento.cuenta.nombre,
                    "debe": Decimal("0.00"),
                    "haber": Decimal("0.00"),
                    "saldo": Decimal("0.00"),
                },
            )
            bucket["debe"] += ContabilidadService._decimal(movimiento.debe)
            bucket["haber"] += ContabilidadService._decimal(movimiento.haber)
            bucket["saldo"] = bucket["debe"] - bucket["haber"]
        return list(mayor.values())

    @staticmethod
    def reporte_balance_comprobacion(*, empresa, fecha_desde=None, fecha_hasta=None):
        """Entrega balance de comprobacion resumido por cuenta."""
        return ContabilidadService.reporte_libro_mayor(
            empresa=empresa,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )

    @staticmethod
    def reporte_estado_resultados(*, empresa, fecha_desde=None, fecha_hasta=None):
        """Construye estado de resultados usando cuentas de ingreso y gasto."""
        balance = ContabilidadService.reporte_balance_comprobacion(
            empresa=empresa,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )

        ingresos = []
        gastos = []
        total_ingresos = Decimal("0.00")
        total_gastos = Decimal("0.00")

        cuentas = {
            cuenta.codigo: cuenta
            for cuenta in PlanCuenta.all_objects.filter(
                empresa=empresa,
                codigo__in=[fila["codigo"] for fila in balance],
            )
        }
        for fila in balance:
            cuenta = cuentas.get(fila["codigo"])
            if not cuenta:
                continue
            saldo = Decimal(fila["saldo"])
            item = {
                "cuenta_id": fila["cuenta_id"],
                "codigo": fila["codigo"],
                "nombre": fila["nombre"],
                "debe": Decimal(fila["debe"]),
                "haber": Decimal(fila["haber"]),
                "saldo": saldo,
            }
            if cuenta.tipo == TipoCuentaContable.INGRESO:
                item["saldo"] = saldo * Decimal("-1")
                total_ingresos += item["saldo"]
                ingresos.append(item)
            elif cuenta.tipo == TipoCuentaContable.GASTO:
                total_gastos += saldo
                gastos.append(item)

        return {
            "ingresos": ingresos,
            "gastos": gastos,
            "total_ingresos": total_ingresos,
            "total_gastos": total_gastos,
            "utilidad": total_ingresos - total_gastos,
        }

    @staticmethod
    @transaction.atomic
    def procesar_solicitudes_pendientes(*, empresa, usuario=None, limit=50):
        """Consume solicitudes del AccountingBridge y crea asientos contabilizados."""
        now = timezone.now()
        eventos = list(
            OutboxEvent.all_objects
            .select_for_update(skip_locked=True)
            .filter(
                empresa=empresa,
                topic="contabilidad",
                event_name="ASIENTO_SOLICITADO",
                status=OutboxStatus.PENDING,
                available_at__lte=now,
            )
            .order_by("available_at", "creado_en")[:limit]
        )

        procesados = []
        for event in eventos:
            event.status = OutboxStatus.PROCESSING
            event.attempts += 1
            event.save(update_fields=["status", "attempts"])

            try:
                entry = event.payload.get("entry") or {}
                movimientos = entry.get("movimientos") or []
                if not movimientos:
                    raise BusinessRuleError("La solicitud contable no contiene movimientos.")

                movimientos_data = []
                for linea in movimientos:
                    movimientos_data.append(
                        {
                            "cuenta": ContabilidadService._resolver_cuenta_linea(
                                empresa=empresa,
                                linea=linea,
                            ),
                            "glosa": linea.get("glosa") or entry.get("glosa") or "",
                            "debe": linea.get("debe", 0),
                            "haber": linea.get("haber", 0),
                        }
                    )

                asiento = ContabilidadService.crear_asiento(
                    empresa=empresa,
                    fecha=entry.get("fecha") or timezone.localdate(),
                    glosa=entry.get("glosa") or f"Asiento {event.payload.get('aggregate_type')}",
                    movimientos_data=movimientos_data,
                    usuario=usuario,
                    referencia_tipo=entry.get("referencia_tipo") or event.payload.get("aggregate_type") or "",
                    referencia_id=event.payload.get("aggregate_id"),
                    origen=OrigenAsientoContable.INTEGRACION,
                )
                ContabilidadService.contabilizar_asiento(
                    asiento_id=asiento.id,
                    empresa=empresa,
                    usuario=usuario,
                )
                ContabilidadService._marcar_origen_contabilizado(
                    aggregate_type=event.payload.get("aggregate_type"),
                    aggregate_id=event.payload.get("aggregate_id"),
                )
                estado_objetivo = entry.get("estado_contable_objetivo")
                if estado_objetivo:
                    module_name = event.payload.get("aggregate_type")
                    if module_name:
                        model_map = {
                            "FacturaVenta": ("apps.ventas.models", "FacturaVenta"),
                            "NotaCreditoVenta": ("apps.ventas.models", "NotaCreditoVenta"),
                            "DocumentoCompraProveedor": ("apps.compras.models", "DocumentoCompraProveedor"),
                            "MovimientoBancario": ("apps.core.models", "MovimientoBancario"),
                        }
                        mapping = model_map.get(module_name)
                        if mapping:
                            module = __import__(mapping[0], fromlist=[mapping[1]])
                            model = getattr(module, mapping[1])
                            model.all_objects.filter(id=event.payload.get("aggregate_id")).update(
                                estado_contable=estado_objetivo,
                            )
                asiento.refresh_from_db()
                OutboxService.mark_sent(event=event)
                procesados.append(asiento)
            except Exception as exc:  # pragma: no cover
                ContabilidadService._marcar_origen_error(
                    aggregate_type=event.payload.get("aggregate_type"),
                    aggregate_id=event.payload.get("aggregate_id"),
                )
                OutboxService.mark_failed(event=event, error_message=str(exc))

        return procesados
