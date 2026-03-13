import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import RequestFactory
from apps.presupuestos.services.presupuesto_service import PresupuestoService
from apps.productos.models import Producto
from apps.presupuestos.models import Presupuesto, PresupuestoItem, EstadoPresupuesto
from apps.core.models import UserEmpresa
from apps.contactos.models.cliente import Cliente
from apps.contactos.models.contacto import Contacto
from apps.core.tenant import set_current_empresa, set_current_user


# =========================================================
# FIXTURES
# =========================================================

@pytest.fixture
def usuario_admin(db, empresa):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    user = User.objects.create_user(
        username="admin",
        email="admin@test.com",
        password="pass",
        empresa_activa=empresa
    )

    UserEmpresa.objects.create(
        user=user,
        empresa=empresa,
        rol="OWNER",
        activo=True
    )

    return user


@pytest.fixture
def cliente(db, empresa):
    set_current_empresa(empresa)

    contacto = Contacto.objects.create(
        nombre="Cliente Test",
        email="cliente@test.com"
    )

    cliente = Cliente.objects.create(
        contacto=contacto
    )

    set_current_empresa(None)
    return cliente


# =========================================================
# TESTS
# =========================================================

@pytest.mark.django_db
class TestPresupuestoService:


    # ------------------------------------------------------

    def test_aprobar_presupuesto_no_descuenta_stock(self, usuario_admin, empresa, cliente):

        set_current_empresa(empresa)
        set_current_user(usuario_admin)

        producto = Producto.objects.create(
            nombre="Producto Test",
            sku="PROD-001",
            stock_actual=Decimal("10.00"),
            maneja_inventario=True
        )

        presupuesto = PresupuestoService.crear_presupuesto(
            data={"cliente": cliente, "fecha": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_admin
        )

        PresupuestoItem.objects.create(
            presupuesto=presupuesto,
            producto=producto,
            descripcion="Test Item",
            cantidad=Decimal("2.00"),
            precio_unitario=Decimal("100.00"),
        )

        PresupuestoService.aprobar_presupuesto(
            presupuesto.id,
            empresa,
            usuario_admin
        )

        producto.refresh_from_db()
        assert producto.stock_actual == Decimal("10.00")

    # ------------------------------------------------------

    def test_anular_presupuesto_no_modifica_stock(self, usuario_admin, empresa, cliente):

        set_current_empresa(empresa)
        set_current_user(usuario_admin)

        producto = Producto.objects.create(
            nombre="Producto Test",
            sku="PROD-001",
            stock_actual=Decimal("10.00"),
            maneja_inventario=True
        )

        presupuesto = PresupuestoService.crear_presupuesto(
            data={"cliente": cliente, "fecha": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_admin
        )

        PresupuestoItem.objects.create(
            presupuesto=presupuesto,
            producto=producto,
            descripcion="Test",
            cantidad=Decimal("3.00"),
            precio_unitario=Decimal("100.00"),
        )

        PresupuestoService.aprobar_presupuesto(presupuesto.id, empresa, usuario_admin)

        producto.refresh_from_db()
        assert producto.stock_actual == Decimal("10.00")

        PresupuestoService.anular_presupuesto(presupuesto.id, empresa, usuario_admin)

        producto.refresh_from_db()
        assert producto.stock_actual == Decimal("10.00")

    # ------------------------------------------------------

    def test_stock_insuficiente_no_bloquea_aprobacion_presupuesto(self, usuario_admin, empresa, cliente):

        set_current_empresa(empresa)
        set_current_user(usuario_admin)

        producto = Producto.objects.create(
            nombre="Producto Escaso",
            sku="ESC-001",
            stock_actual=Decimal("1.00"),
            maneja_inventario=True
        )

        presupuesto = PresupuestoService.crear_presupuesto(
            data={"cliente": cliente, "fecha": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_admin
        )

        PresupuestoItem.objects.create(
            presupuesto=presupuesto,
            producto=producto,
            descripcion="Test Escasez",
            cantidad=Decimal("5.00"),
            precio_unitario=Decimal("100.00"),
        )

        PresupuestoService.aprobar_presupuesto(
            presupuesto.id,
            empresa,
            usuario_admin
        )

        presupuesto.refresh_from_db()
        assert presupuesto.estado == EstadoPresupuesto.APROBADO

        producto.refresh_from_db()
        assert producto.stock_actual == Decimal("1.00")

    # ------------------------------------------------------

    def test_no_se_puede_editar_item_de_presupuesto_aprobado(self, usuario_admin, empresa, cliente):

        set_current_empresa(empresa)
        set_current_user(usuario_admin)

        producto = Producto.objects.create(
            nombre="Prod",
            sku="P1",
            stock_actual=Decimal("10.00"),
            maneja_inventario=True
        )

        presupuesto = PresupuestoService.crear_presupuesto(
            data={"cliente": cliente, "fecha": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_admin
        )

        item = PresupuestoItem.objects.create(
            presupuesto=presupuesto,
            producto=producto,
            descripcion="Descripción obligatoria",
            cantidad=Decimal("5.00"),
            precio_unitario=Decimal("100")
        )

        PresupuestoService.aprobar_presupuesto(
            presupuesto.id,
            empresa,
            usuario_admin
        )

        item.refresh_from_db()
        item.cantidad = Decimal("2.00")

        with pytest.raises(DjangoValidationError):
            item.save()

    def test_aprobar_presupuesto_funciona_sin_contexto_tenant(self, usuario_admin, empresa, cliente):
        set_current_empresa(empresa)
        set_current_user(usuario_admin)

        producto = Producto.objects.create(
            nombre="Producto Async",
            sku="ASYNC-001",
            stock_actual=Decimal("10.00"),
            maneja_inventario=True,
        )

        presupuesto = PresupuestoService.crear_presupuesto(
            data={"cliente": cliente, "fecha": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_admin,
        )

        PresupuestoItem.objects.create(
            presupuesto=presupuesto,
            producto=producto,
            descripcion="Item async",
            cantidad=Decimal("2.00"),
            precio_unitario=Decimal("100.00"),
        )

        # Simulamos ejecución fuera del request (ej. Celery): sin ContextVar tenant.
        set_current_empresa(None)
        set_current_user(None)

        PresupuestoService.aprobar_presupuesto(
            presupuesto.id,
            empresa,
            usuario_admin,
        )

        producto.refresh_from_db()
        assert producto.stock_actual == Decimal("10.00")

    def test_eliminar_presupuesto_aplica_baja_logica(self, usuario_admin, empresa, cliente):
        set_current_empresa(empresa)
        set_current_user(usuario_admin)

        presupuesto = PresupuestoService.crear_presupuesto(
            data={"cliente": cliente, "fecha": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_admin,
        )

        PresupuestoService.eliminar_presupuesto(
            presupuesto_id=presupuesto.id,
            empresa=empresa,
            usuario=usuario_admin,
        )

        presupuesto_refrescado = Presupuesto.all_objects.get(id=presupuesto.id)
        assert presupuesto_refrescado.estado == EstadoPresupuesto.ANULADO
