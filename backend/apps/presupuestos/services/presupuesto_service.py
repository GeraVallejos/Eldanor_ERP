from django.db import transaction
from django.db.models import Max
from apps.core.exceptions import AuthorizationError, BusinessRuleError
from apps.auditoria.services import AuditoriaService
from apps.auditoria.models import AuditSeverity
from apps.presupuestos.models import EstadoPresupuesto
from apps.core.services.secuencia_service import SecuenciaService
from apps.presupuestos.models import Presupuesto, PresupuestoItem, PresupuestoHistorial
from apps.core.permisos.constantes_permisos import Acciones, Modulos


class PresupuestoService:

    ESTADOS_TRANSICION_VALIDA = {
        EstadoPresupuesto.BORRADOR: {
            EstadoPresupuesto.ENVIADO,
            EstadoPresupuesto.APROBADO,
            EstadoPresupuesto.ANULADO,
        },
        EstadoPresupuesto.ENVIADO: {
            EstadoPresupuesto.BORRADOR,
            EstadoPresupuesto.APROBADO,
            EstadoPresupuesto.RECHAZADO,
        },
        EstadoPresupuesto.RECHAZADO: {EstadoPresupuesto.BORRADOR, EstadoPresupuesto.ENVIADO},
        EstadoPresupuesto.APROBADO: {EstadoPresupuesto.ANULADO},
        EstadoPresupuesto.ANULADO: set(),
    }

    @staticmethod
    def _es_ultimo_folio(presupuesto):

        max_numero = (
            Presupuesto.all_objects
            .filter(empresa=presupuesto.empresa)
            .aggregate(max_numero=Max("numero"))
        )["max_numero"]

        return max_numero is not None and presupuesto.numero == max_numero

    # ===============================
    # Públicos
    # ===============================

    @staticmethod
    def _items_queryset(presupuesto):
        # Evita dependencia del manager filtrado por ContextVar en servicios async.
        return PresupuestoItem.all_objects.filter(
            presupuesto=presupuesto,
            empresa=presupuesto.empresa,
        )

    @staticmethod
    @transaction.atomic
    def crear_presupuesto(data, empresa, usuario):

        if not usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.CREAR, empresa):
            raise AuthorizationError("No tiene permisos para crear presupuestos.")

        numero = SecuenciaService.obtener_siguiente_numero(
            empresa=empresa,
            tipo_documento="PRESUPUESTO"
        )

        return Presupuesto.objects.create(
            numero=numero,
            empresa=empresa,
            creado_por=usuario,
            cliente=data["cliente"],
            estado=EstadoPresupuesto.BORRADOR,
            fecha=data["fecha"],
            descuento=data.get("descuento", 0),
            observaciones=data.get("observaciones", ""),
            fecha_vencimiento=data.get("fecha_vencimiento"),
        )


    @staticmethod
    @transaction.atomic
    def aprobar_presupuesto(presupuesto_id, empresa, usuario):
        # 1. Traer el objeto y bloquearlo para edición
        presupuesto = Presupuesto.all_objects.select_for_update().get(id=presupuesto_id, empresa=empresa)

        if not usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.APROBAR, empresa):
            raise AuthorizationError("No tiene permisos para aprobar presupuestos.")

        # 2. Validaciones de negocio
        if not PresupuestoService._items_queryset(presupuesto).exists():
            raise BusinessRuleError("No se puede aprobar un presupuesto sin ítems.")
        
        if presupuesto.estado not in (EstadoPresupuesto.BORRADOR, EstadoPresupuesto.ENVIADO):
            raise BusinessRuleError("Solo se pueden aprobar presupuestos en estado Borrador o Enviado.")

        # 3. Capturar cambios para el historial usando el Mixin
        # Seteamos el nuevo estado temporalmente en la instancia para que el Mixin vea la diferencia
        estado_anterior = presupuesto.estado
        presupuesto.estado = EstadoPresupuesto.APROBADO
        cambios = presupuesto.get_dirty_fields() 

        # 4. Guardar presupuesto
        presupuesto.save(update_fields=["estado"])

        # 5. Registrar historial detallado
        PresupuestoService.registrar_historial(
            presupuesto, usuario, estado_anterior, EstadoPresupuesto.APROBADO, cambios
        )

        return presupuesto

    @staticmethod
    @transaction.atomic
    def cambiar_estado_presupuesto(presupuesto_id, nuevo_estado, empresa, usuario):
        presupuesto = Presupuesto.all_objects.select_for_update().get(id=presupuesto_id, empresa=empresa)

        estado_actual = presupuesto.estado
        nuevo_estado = str(nuevo_estado or "").strip().upper()

        estados_validos = {valor for valor, _ in EstadoPresupuesto.choices}
        if nuevo_estado not in estados_validos:
            raise BusinessRuleError("Estado de presupuesto invalido.")

        if nuevo_estado == estado_actual:
            return presupuesto

        permitidos = PresupuestoService.ESTADOS_TRANSICION_VALIDA.get(estado_actual, set())
        if nuevo_estado not in permitidos:
            raise BusinessRuleError(
                f"No se puede cambiar de {estado_actual} a {nuevo_estado} con las reglas actuales."
            )

        if nuevo_estado == EstadoPresupuesto.APROBADO:
            return PresupuestoService.aprobar_presupuesto(
                presupuesto_id=presupuesto_id,
                empresa=empresa,
                usuario=usuario,
            )

        if nuevo_estado == EstadoPresupuesto.ANULADO:
            PresupuestoService.anular_presupuesto(
                presupuesto_id=presupuesto_id,
                empresa=empresa,
                usuario=usuario,
            )
            return Presupuesto.all_objects.get(id=presupuesto_id, empresa=empresa)

        if not usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.EDITAR, empresa):
            raise AuthorizationError("No tiene permisos para cambiar el estado del presupuesto.")

        estado_anterior = presupuesto.estado
        presupuesto.estado = nuevo_estado
        cambios = presupuesto.get_dirty_fields()
        presupuesto.save(update_fields=["estado"])

        PresupuestoService.registrar_historial(
            presupuesto,
            usuario,
            estado_anterior,
            nuevo_estado,
            cambios,
        )

        return presupuesto

    @staticmethod
    @transaction.atomic
    def anular_presupuesto(presupuesto_id, empresa, usuario):

        presupuesto = (
            Presupuesto.all_objects
            .select_for_update()
            .get(pk=presupuesto_id, empresa=empresa)
        )

        # Seguridad: Solo ciertos roles pueden anular
        if not usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.ANULAR, empresa):
            raise AuthorizationError("No tiene permisos para anular presupuestos")

        # Regla de negocio: se permite anular desde borrador/enviado/aprobado.
        if presupuesto.estado not in (
            EstadoPresupuesto.BORRADOR,
            EstadoPresupuesto.ENVIADO,
            EstadoPresupuesto.APROBADO,
        ):
            raise BusinessRuleError(
                f"Solo se pueden anular presupuestos en estado borrador, enviado o aprobado. Estado actual: {presupuesto.estado}"
            )

        estado_anterior = presupuesto.estado
        presupuesto.estado = EstadoPresupuesto.ANULADO
        presupuesto.save(update_fields=["estado"])

        PresupuestoService.registrar_historial(
            presupuesto,
            usuario,
            estado_anterior,
            EstadoPresupuesto.ANULADO,
            cambios={"estado": [estado_anterior, EstadoPresupuesto.ANULADO]},
        )

    @staticmethod
    @transaction.atomic
    def eliminar_presupuesto(presupuesto_id, empresa, usuario):
        # Eliminacion logica controlada por reglas de negocio (sin hard delete).
        presupuesto = Presupuesto.all_objects.select_for_update().get(pk=presupuesto_id, empresa=empresa)

        # Seguridad: Solo ciertos roles pueden eliminar
        if not usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.BORRAR, empresa):
            raise AuthorizationError("No tiene permisos para eliminar presupuestos")

        # Seguridad de folios: si esta aprobado solo se permite borrar el ultimo para trazabilidad.
        if presupuesto.estado == EstadoPresupuesto.APROBADO and not PresupuestoService._es_ultimo_folio(presupuesto):
            raise BusinessRuleError("No se puede eliminar un presupuesto aprobado que no sea el último. Debe anularlo.")

        if presupuesto.estado == EstadoPresupuesto.ANULADO:
            return

        if presupuesto.estado not in {
            EstadoPresupuesto.BORRADOR,
            EstadoPresupuesto.ENVIADO,
            EstadoPresupuesto.RECHAZADO,
            EstadoPresupuesto.APROBADO,
        }:
            raise BusinessRuleError(
                f"No se puede eliminar lógicamente un presupuesto en estado {presupuesto.estado}."
            )

        estado_anterior = presupuesto.estado
        presupuesto.estado = EstadoPresupuesto.ANULADO
        presupuesto.save(update_fields=["estado"])

        # Registro de auditoría de baja lógica.
        PresupuestoService.registrar_historial(
            presupuesto,
            usuario,
            estado_anterior,
            EstadoPresupuesto.ANULADO,
            cambios={
                "sistema": "Baja logica solicitada desde destroy",
                "estado": [estado_anterior, EstadoPresupuesto.ANULADO],
            },
        )

    @staticmethod
    @transaction.atomic
    def clonar_presupuesto(presupuesto_id, empresa, usuario):
        """
        Crea una copia exacta de un presupuesto (en estado BORRADOR) 
        con un nuevo número de folio.
        """
        original = Presupuesto.all_objects.get(id=presupuesto_id, empresa=empresa)

        if not PresupuestoService._items_queryset(original).exists():
            raise BusinessRuleError("No se puede clonar un presupuesto sin ítems.")
        
        if not usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.CREAR, empresa):
            raise AuthorizationError("No tiene permisos para crear presupuestos.")
        
        # 1. Obtener nuevo número
        nuevo_numero = SecuenciaService.obtener_siguiente_numero(
            empresa=empresa, tipo_documento="PRESUPUESTO"
        )
        
        # 2. Crear el nuevo encabezado (Copia casi todo del original)
        nuevo_presupuesto = Presupuesto.objects.create(
            numero=nuevo_numero,
            empresa=empresa,
            cliente=original.cliente,
            fecha=original.fecha,
            fecha_vencimiento=original.fecha_vencimiento,
            observaciones=f"Copia de presupuesto N°{original.numero}. {original.observaciones}",
            creado_por=usuario,
            estado=EstadoPresupuesto.BORRADOR # Siempre empieza como borrador
        )
        
        # 3. Clonar los ítems
        for item in PresupuestoService._items_queryset(original):
            PresupuestoItem.objects.create(
                presupuesto=nuevo_presupuesto,
                producto=item.producto,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                descuento=item.descuento,
                impuesto=item.impuesto,
            )
            
        return nuevo_presupuesto
    
    @staticmethod
    def registrar_cambio_estado(presupuesto, usuario, anterior, nuevo):
        PresupuestoHistorial.objects.create(
            presupuesto=presupuesto,
            usuario=usuario,
            estado_anterior=anterior,
            estado_nuevo=nuevo,
            empresa=presupuesto.empresa
        )

    @staticmethod
    def registrar_historial(presupuesto, usuario, estado_anterior, estado_nuevo, cambios=None):
        """
        Registro centralizado de historial con soporte para cambios detallados.
        """
        from apps.presupuestos.models import PresupuestoHistorial
        from apps.core.services import DomainEventService, OutboxService
        
        historial = PresupuestoHistorial.objects.create(
            presupuesto=presupuesto,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            cambios=cambios,  # Aquí va el JSON del Mixin
            empresa=presupuesto.empresa
        )

        payload = {
            "presupuesto_id": str(presupuesto.id),
            "numero": presupuesto.numero,
            "estado_anterior": estado_anterior,
            "estado_nuevo": estado_nuevo,
            "cambios": cambios or {},
        }
        DomainEventService.record_event(
            empresa=presupuesto.empresa,
            aggregate_type="PRESUPUESTO",
            aggregate_id=presupuesto.id,
            event_type=f"PRESUPUESTO_ESTADO_{str(estado_nuevo).upper()}",
            payload=payload,
            meta={"source": "PresupuestoService.registrar_historial"},
            usuario=usuario,
        )

        OutboxService.enqueue(
            empresa=presupuesto.empresa,
            topic="presupuestos",
            event_name="PRESUPUESTO_ESTADO_CAMBIADO",
            payload=payload,
            usuario=usuario,
            dedup_key=f"presupuesto-historial:{historial.id}",
        )

        accion_auditoria = {
            EstadoPresupuesto.APROBADO: Acciones.APROBAR,
            EstadoPresupuesto.ANULADO: Acciones.ANULAR,
        }.get(estado_nuevo, Acciones.EDITAR)

        AuditoriaService.registrar_evento(
            empresa=presupuesto.empresa,
            usuario=usuario,
            module_code=Modulos.PRESUPUESTOS,
            action_code=accion_auditoria,
            event_type=f"PRESUPUESTO_ESTADO_{str(estado_nuevo).upper()}",
            entity_type="PRESUPUESTO",
            entity_id=str(presupuesto.id),
            summary=f"Presupuesto {presupuesto.numero} cambio de {estado_anterior} a {estado_nuevo}.",
            severity=AuditSeverity.INFO,
            changes=cambios or {},
            payload=payload,
            meta={"source": "PresupuestoService.registrar_historial", "historial_id": str(historial.id)},
            source="PresupuestoService.registrar_historial",
            idempotency_key=f"audit:presupuesto-historial:{historial.id}",
        )
