import pytest
from datetime import timedelta
from django.utils import timezone

from apps.auditoria.models import AuditEvent, AuditSeverity
from apps.auditoria.services import AuditoriaService
from apps.core.exceptions import BusinessRuleError


@pytest.mark.django_db
class TestAuditoriaService:
    def test_registra_evento_con_hash_chain(self, empresa, usuario):
        evento_1 = AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="PRESUPUESTOS",
            action_code="APROBAR",
            event_type="PRESUPUESTO_APROBADO",
            entity_type="PRESUPUESTO",
            entity_id="100",
            summary="Presupuesto aprobado por flujo",
        )

        evento_2 = AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="PRESUPUESTOS",
            action_code="ANULAR",
            event_type="PRESUPUESTO_ANULADO",
            entity_type="PRESUPUESTO",
            entity_id="100",
            summary="Presupuesto anulado por regla",
        )

        assert evento_1.previous_hash == ""
        assert evento_2.previous_hash == evento_1.event_hash
        assert evento_1.event_hash
        assert evento_2.event_hash

    def test_idempotencia_retorna_mismo_evento(self, empresa, usuario):
        a = AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="INVENTARIO",
            action_code="ENTRADA",
            event_type="INVENTARIO_MOVIMIENTO_REGISTRADO",
            entity_type="MOVIMIENTO",
            entity_id="mv-1",
            summary="Entrada de stock",
            idempotency_key="aud:inv:1",
        )

        b = AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="INVENTARIO",
            action_code="ENTRADA",
            event_type="INVENTARIO_MOVIMIENTO_REGISTRADO",
            entity_type="MOVIMIENTO",
            entity_id="mv-1",
            summary="Entrada de stock duplicada",
            idempotency_key="aud:inv:1",
        )

        assert a.id == b.id

    def test_valida_campos_requeridos(self, empresa, usuario):
        with pytest.raises(BusinessRuleError):
            AuditoriaService.registrar_evento(
                empresa=empresa,
                usuario=usuario,
                module_code="",
                action_code="CREAR",
                event_type="CLIENTE_CREADO",
                entity_type="CLIENTE",
            )

    def test_verifica_cadena_integridad(self, empresa, usuario):
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="CONTACTOS",
            action_code="CREAR",
            event_type="CLIENTE_CREADO",
            entity_type="CLIENTE",
            entity_id="cli-1",
            severity=AuditSeverity.INFO,
            summary="Cliente creado",
        )
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="CONTACTOS",
            action_code="ACTUALIZAR",
            event_type="CLIENTE_ACTUALIZADO",
            entity_type="CLIENTE",
            entity_id="cli-1",
            severity=AuditSeverity.WARNING,
            summary="Cliente actualizado",
        )

        result = AuditoriaService.verificar_cadena_integridad(empresa=empresa)

        assert result["is_valid"] is True
        assert result["total_events"] == 2
        assert result["inconsistencies"] == []
        assert result["is_partial_scan"] is False

    def test_verifica_cadena_integridad_limit_parcial(self, empresa, usuario):
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="CONTACTOS",
            action_code="CREAR",
            event_type="CLIENTE_CREADO",
            entity_type="CLIENTE",
            entity_id="cli-1",
            summary="Cliente creado",
        )
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="CONTACTOS",
            action_code="EDITAR",
            event_type="CLIENTE_ACTUALIZADO",
            entity_type="CLIENTE",
            entity_id="cli-1",
            summary="Cliente actualizado",
        )

        result = AuditoriaService.verificar_cadena_integridad(empresa=empresa, limit=1)

        assert result["is_valid"] is True
        assert result["total_events"] == 1
        assert result["is_partial_scan"] is True

    def test_verifica_cadena_integridad_limit_invalido(self, empresa, usuario):
        AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="CONTACTOS",
            action_code="CREAR",
            event_type="CLIENTE_CREADO",
            entity_type="CLIENTE",
            entity_id="cli-1",
            summary="Cliente creado",
        )

        with pytest.raises(BusinessRuleError):
            AuditoriaService.verificar_cadena_integridad(empresa=empresa, limit="0")

    def test_verifica_cadena_integridad_avanzada_rango_y_bloques(self, empresa, usuario):
        evento_1 = AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="CONTACTOS",
            action_code="CREAR",
            event_type="CLIENTE_CREADO",
            entity_type="CLIENTE",
            entity_id="cli-1",
            summary="Cliente creado",
        )
        evento_2 = AuditoriaService.registrar_evento(
            empresa=empresa,
            usuario=usuario,
            module_code="CONTACTOS",
            action_code="EDITAR",
            event_type="CLIENTE_ACTUALIZADO",
            entity_type="CLIENTE",
            entity_id="cli-1",
            summary="Cliente actualizado",
        )

        # Garantiza que el rango arranque en el segundo evento para validar anclaje.
        now = timezone.now()
        AuditEvent.all_objects.filter(id=evento_1.id).update(occurred_at=now - timedelta(minutes=2))
        AuditEvent.all_objects.filter(id=evento_2.id).update(occurred_at=now - timedelta(minutes=1))

        result = AuditoriaService.verificar_cadena_integridad_avanzada(
            empresa=empresa,
            date_from=now - timedelta(minutes=1, seconds=5),
            include_blocks=True,
            block_size=1,
        )

        assert result["is_valid"] is True
        assert result["has_range_filter"] is True
        assert result["total_events"] == 1
        assert len(result["blocks"]) == 1
        assert result["blocks"][0]["total_events"] == 1
