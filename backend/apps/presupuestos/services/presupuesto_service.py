from django.db import transaction
from django.db.models import Max
from apps.core.exceptions import AuthorizationError, BusinessRuleError
from apps.documentos.models import TipoDocumentoReferencia
from apps.presupuestos.models import EstadoPresupuesto
from apps.inventario.models import MovimientoInventario, TipoMovimiento
from apps.core.services.secuencia_service import SecuenciaService
from apps.presupuestos.models import Presupuesto, PresupuestoItem, PresupuestoHistorial
from apps.inventario.services.inventario_service import InventarioService
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

    @staticmethod
    def _revertir_inventario(presupuesto, usuario):

        referencia = f"PRESUPUESTO-{presupuesto.numero}"

        movimientos = MovimientoInventario.all_objects.filter(
            empresa=presupuesto.empresa,
            referencia=referencia
        )

        for movimiento in movimientos:

            tipo_reverso = (
                TipoMovimiento.ENTRADA
                if movimiento.tipo == TipoMovimiento.SALIDA
                else TipoMovimiento.SALIDA
            )

            InventarioService.registrar_movimiento(
                producto_id=movimiento.producto.id,
                bodega_id=movimiento.bodega_id,
                tipo=tipo_reverso,
                cantidad=movimiento.cantidad,
                referencia=f"REVERSO-{referencia}",
                empresa=presupuesto.empresa,
                usuario=usuario,
                documento_tipo=TipoDocumentoReferencia.PRESUPUESTO,
                documento_id=presupuesto.id,
            )

        movimientos.delete()

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

        # 4. Procesar inventario
        for item in PresupuestoService._items_queryset(presupuesto):
            if item.producto and item.producto.maneja_inventario:
                InventarioService.registrar_movimiento(
                    producto_id=item.producto.id,
                    tipo=TipoMovimiento.SALIDA,
                    cantidad=item.cantidad,
                    referencia=f"PRESUPUESTO-{presupuesto.numero}",
                    empresa=empresa,
                    usuario=usuario,
                    documento_tipo=TipoDocumentoReferencia.PRESUPUESTO,
                    documento_id=presupuesto.id,
                )

        # 5. Guardar presupuesto
        presupuesto.save(update_fields=["estado"])

        # 6. Registrar historial detallado
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

        # Si estaba aprobado pudo impactar inventario.
        if presupuesto.estado == EstadoPresupuesto.APROBADO:
            PresupuestoService._revertir_inventario(presupuesto, usuario)

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
        # Eliminacion fisica (hard delete) controlada por reglas de negocio
        presupuesto = Presupuesto.all_objects.select_for_update().get(pk=presupuesto_id, empresa=empresa)

        # Seguridad: Solo ciertos roles pueden eliminar
        if not usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.BORRAR, empresa):
            raise AuthorizationError("No tiene permisos para eliminar presupuestos")

        # SEGURIDAD DE INVENTARIO
        if presupuesto.estado == EstadoPresupuesto.APROBADO:
            # Si el ERP permite borrar algo aprobado (solo el último folio),
            # DEBEMOS devolver la mercadería al estante.
            if not PresupuestoService._es_ultimo_folio(presupuesto):
                  raise BusinessRuleError("No se puede eliminar un presupuesto aprobado que no sea el último. Debe anularlo.")
            
            PresupuestoService._revertir_inventario(presupuesto, usuario)

        # Registro de auditoría final antes de desaparecer
        PresupuestoService.registrar_historial(
            presupuesto, usuario, presupuesto.estado, "ELIMINADO", 
            cambios={"sistema": "Registro marcado como eliminado"}
        )

        presupuesto.delete()  # Hard delete

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
        
        PresupuestoHistorial.objects.create(
            presupuesto=presupuesto,
            usuario=usuario,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            cambios=cambios,  # Aquí va el JSON del Mixin
            empresa=presupuesto.empresa
        )
