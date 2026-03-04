import pytest
from decimal import Decimal
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.presupuestos.services.presupuesto_service import PresupuestoService
from apps.productos.models import Producto
from apps.presupuestos.models import PresupuestoItem, EstadoPresupuesto
from apps.core.models import Empresa, User, RolUsuario
from apps.contactos.models.cliente import Cliente
from apps.contactos.models.contacto import Contacto
from apps.core.tenant import set_current_empresa, set_current_user


# --- Fixtures ---

@pytest.fixture
def empresa(db):
    return Empresa.objects.create(nombre="Empresa Test", rut="12345678-9")

@pytest.fixture
def usuario_admin(db, empresa):
    return User.objects.create(
        username="admin_test",
        empresa=empresa,
        rol=RolUsuario.ADMIN
    )

@pytest.fixture
def cliente(db, empresa):
    contacto = Contacto.objects.create(
        empresa=empresa,
        nombre="Cliente Test",
        email="cliente@test.com"
    )
    return Cliente.objects.create(
        empresa=empresa,
        contacto=contacto
    )

# --- Tests ---

@pytest.mark.django_db
class TestPresupuestoService:

    def setup_method(self):
        set_current_empresa(None)
        set_current_user(None)

    def test_aprobar_presupuesto_descuenta_stock(self, usuario_admin, empresa, cliente):
        set_current_empresa(empresa)
        set_current_user(usuario_admin)

        # 1. Preparar Producto
        producto = Producto.objects.create(
            nombre="Producto Test",
            sku="PROD-001",
            empresa=empresa,
            stock_actual=Decimal("10.00"),
            maneja_inventario=True
        )

        # 2. Crear Presupuesto (Borrador)
        presupuesto = PresupuestoService.crear_presupuesto(
            data={"cliente": cliente, "fecha": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_admin
        )

        # 3. CREAR EL ÍTEM ANTES DE APROBAR
        PresupuestoItem.objects.create(
            presupuesto=presupuesto,
            producto=producto,
            descripcion="Test Item",
            cantidad=Decimal("2.00"),
            precio_unitario=Decimal("100.00"),
        )

        # 4. Actuar: Aprobar
        # El service ahora sí encontrará ítems para procesar inventario
        PresupuestoService.aprobar_presupuesto(presupuesto.id, empresa, usuario_admin)

        # 5. Verificar
        producto.refresh_from_db()
        assert producto.stock_actual == Decimal("8.00")

    def test_anular_presupuesto_revierte_stock(self, usuario_admin, empresa, cliente):
        set_current_empresa(empresa)
        set_current_user(usuario_admin)

        producto = Producto.objects.create(
            nombre="Producto Test",
            sku="PROD-001",
            empresa=empresa,
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

        # Flujo completo: Aprobar (baja stock) -> Anular (sube stock)
        PresupuestoService.aprobar_presupuesto(presupuesto.id, empresa, usuario_admin)
        
        producto.refresh_from_db()
        assert producto.stock_actual == Decimal("7.00")

        PresupuestoService.anular_presupuesto(presupuesto.id, empresa, usuario_admin)

        producto.refresh_from_db()
        assert producto.stock_actual == Decimal("10.00")

    def test_no_puede_eliminar_si_no_es_ultimo(self, usuario_admin, empresa, cliente):
        set_current_empresa(empresa)
        set_current_user(usuario_admin)

        # Crear dos presupuestos seguidos
        p1 = PresupuestoService.crear_presupuesto(
            data={"cliente": cliente, "fecha": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_admin
        )
        p2 = PresupuestoService.crear_presupuesto(
            data={"cliente": cliente, "fecha": "2026-01-01"},
            empresa=empresa,
            usuario=usuario_admin
        )

        # IMPORTANTE: Según tu Service, el chequeo de 'ultimo_folio' se hace
        # si el estado es APROBADO. Vamos a forzar el estado para que entre en la validación.
        p1.estado = EstadoPresupuesto.APROBADO
        p1.save()
        p2.estado = EstadoPresupuesto.APROBADO
        p2.save()

        # Intentar eliminar p1 (folio anterior) cuando p2 existe (folio más reciente)
        with pytest.raises(ValidationError) as excinfo:
            PresupuestoService.eliminar_presupuesto(
                p1.id,
                empresa,
                usuario_admin
            )
        
        # Verificamos que el mensaje de error sea el esperado
        assert "No se puede eliminar un presupuesto aprobado que no sea el último" in str(excinfo.value)


    def test_error_stock_insuficiente_no_aprueba_presupuesto(self,usuario_admin, empresa, cliente):
            set_current_empresa(empresa)
            set_current_user(usuario_admin)

            # 1. Producto con poco stock (solo 1 unidad)
            producto = Producto.objects.create(
                nombre="Producto Escaso",
                sku="ESC-001",
                empresa=empresa,
                stock_actual=Decimal("1.00"),
                impuesto=None,
                maneja_inventario=True
            )

            # 2. Crear Presupuesto
            presupuesto = PresupuestoService.crear_presupuesto(
                data={"cliente": cliente, "fecha": "2026-01-01"},
                empresa=empresa,
                usuario=usuario_admin
            )

            # 3. Agregar ítem que pide MÁS de lo que hay (pide 5, hay 1)
            PresupuestoItem.objects.create(
                presupuesto=presupuesto,
                producto=producto,
                descripcion="Test Escasez",
                cantidad=Decimal("5.00"),
                precio_unitario=Decimal("100.00"),
            )

            # 4. Actuar: Intentar aprobar debe lanzar ValidationError
            # Importante: debe ser la ValidationError que lance tu InventarioService
            with pytest.raises(DjangoValidationError) as excinfo:
                PresupuestoService.aprobar_presupuesto(presupuesto.id, empresa, usuario_admin)
            
            # Opcional: verificar que el mensaje mencione el stock
            assert "insuficiente" in str(excinfo.value).lower()

            # 5. VERIFICACIÓN CRÍTICA:
            # El presupuesto NO debe haber cambiado de estado (debe seguir en BORRADOR)
            presupuesto.refresh_from_db()
            assert presupuesto.estado == EstadoPresupuesto.BORRADOR
            
            # El stock del producto debe seguir intacto (1.00)
            producto.refresh_from_db()
            assert producto.stock_actual == Decimal("1.00")


    def test_fallo_en_un_item_revierte_todos_los_movimientos(self,usuario_admin, empresa, cliente):
            set_current_empresa(empresa)
            set_current_user(usuario_admin)

            # 1. Crear dos productos con stock suficiente
            p1 = Producto.objects.create(
                nombre="Producto A", sku="A", empresa=empresa,
                stock_actual=Decimal("10.00"), maneja_inventario=True
            )
            p2 = Producto.objects.create(
                nombre="Producto B", sku="B", empresa=empresa,
                stock_actual=Decimal("10.00"), maneja_inventario=True
            )
            # 2. Crear un producto SIN stock
            p3 = Producto.objects.create(
                nombre="Producto C", sku="C", empresa=empresa,
                stock_actual=Decimal("0.00"), maneja_inventario=True
            )

            # 3. Crear Presupuesto
            presupuesto = PresupuestoService.crear_presupuesto(
                data={"cliente": cliente, "fecha": "2026-01-01"},
                empresa=empresa, usuario=usuario_admin
            )

            # 4. Agregar los 3 ítems
            for p in [p1, p2, p3]:
                PresupuestoItem.objects.create(
                    presupuesto=presupuesto, producto=p,
                    descripcion=f"Item {p.sku}", cantidad=Decimal("5.00"),
                    precio_unitario=Decimal("100.00")
                )

            # 5. Actuar: Intentar aprobar (fallará en el tercer ítem)
            with pytest.raises(DjangoValidationError):
                PresupuestoService.aprobar_presupuesto(presupuesto.id, empresa, usuario_admin)

            # 6. VERIFICACIÓN: Ningún stock debe haber bajado
            p1.refresh_from_db()
            p2.refresh_from_db()
            p3.refresh_from_db()
            
            assert p1.stock_actual == Decimal("10.00"), "El producto 1 no debió descontar stock"
            assert p2.stock_actual == Decimal("10.00"), "El producto 2 no debió descontar stock"
            
            # 7. Verificar que no existan movimientos en la DB para este presupuesto
            from apps.productos.models import MovimientoInventario
            movimientos = MovimientoInventario.objects.filter(referencia=f"PRESUPUESTO-{presupuesto.numero}")
            assert movimientos.count() == 0, "No deberían existir registros de movimientos (Kardex)"

    
    def test_no_se_puede_editar_item_de_presupuesto_aprobado(self, usuario_admin, empresa, cliente):
        set_current_empresa(empresa)
        set_current_user(usuario_admin)

        # 1. Crear presupuesto y aprobarlo
        producto = Producto.objects.create(
            nombre="Prod", sku="P1", empresa=empresa,
            stock_actual=Decimal("10.00"), maneja_inventario=True
        )
        presupuesto = PresupuestoService.crear_presupuesto(
            data={"cliente": cliente, "fecha": "2026-01-01"},
            empresa=empresa, usuario=usuario_admin
        )
        item = PresupuestoItem.objects.create(
            presupuesto=presupuesto, producto=producto,
            descripcion="Descripción obligatoria",
            cantidad=Decimal("5.00"), precio_unitario=Decimal("100")
        )
        item = PresupuestoItem.objects.create(
            presupuesto=presupuesto, producto=producto,
            descripcion="Descripción obligatoria",
            cantidad=Decimal("5.00"), precio_unitario=Decimal("100")
        )

        # 1. Aprobamos vía Service (esto cambia la DB)
        PresupuestoService.aprobar_presupuesto(presupuesto.id, empresa, usuario_admin)

        # 2. !!! CRÍTICO !!! 
        # Refrescamos el ítem desde la DB para que sepa que su presupuesto ya está APROBADO
        item.refresh_from_db()

        # 3. Intentar cambiar la cantidad
        item.cantidad = Decimal("2.00")
        
        with pytest.raises(DjangoValidationError):
            item.save()
