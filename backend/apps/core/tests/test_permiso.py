import pytest
from django.contrib.auth import get_user_model
from apps.core.models import Empresa, UserEmpresa, PermisoModulo
from apps.core.roles import RolUsuario
from apps.core.permisos.constantes_permisos import Modulos, Acciones
from apps.presupuestos.services.presupuesto_service import PresupuestoService
from apps.presupuestos.models.presupuesto import EstadoPresupuesto, Presupuesto
from apps.productos.models import Producto
from apps.presupuestos.models import PresupuestoItem
from apps.contactos.models.cliente import Cliente
from datetime import date
from apps.contactos.models.contacto import Contacto
from apps.core.tenant import set_current_empresa


User = get_user_model()


# =========================================================
# FIXTURES
# =========================================================


@pytest.fixture
def usuario(db):
    return User.objects.create_user(
        username="testuser",
        email="test@test.com",
        password="1234"
    )


def crear_relacion(usuario, empresa, rol):
    return UserEmpresa.objects.create(
        user=usuario,
        empresa=empresa,
        rol=rol,
        activo=True
    )

@pytest.fixture
def empresa():
    return Empresa.objects.create(
        nombre="Empresa Test",
        rut="11111111-1",
        email="empresa@test.com"
    )


@pytest.fixture
def empresa_b():
    return Empresa.objects.create(
        nombre="Empresa B",
        rut="22222222-2",
        email="empresa_b@test.com"
    )

@pytest.fixture
def usuario_owner(usuario, empresa):
    UserEmpresa.objects.create(
        user=usuario,
        empresa=empresa,
        rol=RolUsuario.OWNER,
        activo=True
    )
    return usuario


@pytest.fixture
def usuario_admin(usuario, empresa):
    UserEmpresa.objects.create(
        user=usuario,
        empresa=empresa,
        rol=RolUsuario.ADMIN,
        activo=True
    )
    return usuario


@pytest.fixture
def usuario_vendedor(usuario, empresa):
    UserEmpresa.objects.create(
        user=usuario,
        empresa=empresa,
        rol=RolUsuario.VENDEDOR,
        activo=True
    )
    return usuario


@pytest.fixture
def usuario_admin_inactivo(usuario, empresa):
    UserEmpresa.objects.create(
        user=usuario,
        empresa=empresa,
        rol=RolUsuario.ADMIN,
        activo=False
    )
    return usuario

@pytest.fixture
def usuario_owner_empresa_a(empresa, empresa_b):
    user = User.objects.create_user(
        email="owner@test.com",
        username="owner@test.com",
        password="123456"
    )

    UserEmpresa.objects.create(
        user=user,
        empresa=empresa,
        rol=RolUsuario.OWNER,
        activo=True
    )

    return user



@pytest.fixture
def producto(empresa):
    return Producto.objects.create(
        empresa=empresa,
        nombre="Producto Test",
        precio_referencia=1000,
        stock_actual=10,
        sku="PROD-001",
    )

@pytest.fixture
def cliente(empresa):

    contacto = Contacto.objects.create(
        empresa=empresa,
        nombre="Cliente Test",
        rut="12345678-9",
        email="cliente@test.com"
    )

    return Cliente.objects.create(
        empresa=empresa,
        contacto=contacto,
        limite_credito=0,
        dias_credito=0
    )

@pytest.fixture
def presupuesto_borrador(empresa, cliente, usuario):
    return Presupuesto.objects.create(
        empresa=empresa,
        cliente=cliente,
        numero=1,
        fecha=date.today(),
        estado=EstadoPresupuesto.BORRADOR,
        creado_por=usuario
    )

@pytest.fixture
def cliente_empresa_b(empresa_b):
    contacto = Contacto.objects.create(
        empresa=empresa_b,
        nombre="Cliente B",
        rut="98765432-1",
        email="cliente_b@test.com"
    )

    return Cliente.objects.create(
        empresa=empresa_b,
        contacto=contacto
    )


@pytest.fixture
def presupuesto_empresa_b(empresa_b, cliente_empresa_b, usuario_owner_empresa_a):
    from datetime import date

    return Presupuesto.objects.create(
        empresa=empresa_b,
        cliente=cliente_empresa_b,
        numero=1,
        fecha=date.today(),
        estado=EstadoPresupuesto.BORRADOR,
        creado_por=usuario_owner_empresa_a
    )

@pytest.fixture
def detalle_presupuesto(presupuesto_borrador, producto, precio_unitario):
    return PresupuestoItem.objects.create(
        presupuesto=presupuesto_borrador,
        producto=producto,
        cantidad=2,
        precio_unitario=precio_unitario
    )

@pytest.fixture
def empresa_activa():

    def activar(empresa):
        set_current_empresa(empresa)
        return empresa
    yield activar
    set_current_empresa(None)

# =========================================================
# TESTS
# =========================================================

@pytest.mark.django_db
class TestPermisos:

    def test_owner_tiene_todos_los_permisos(self, usuario, empresa):

        crear_relacion(usuario, empresa, RolUsuario.OWNER)

        assert usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.CREAR, empresa)
        assert usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.APROBAR, empresa)
        assert usuario.tiene_permiso(Modulos.PRODUCTOS, Acciones.BORRAR, empresa)
        assert usuario.tiene_permiso(Modulos.CONTACTOS, Acciones.ANULAR, empresa)


    def test_admin_tiene_todos_los_permisos(self, usuario, empresa):

        crear_relacion(usuario, empresa, RolUsuario.ADMIN)

        assert usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.CREAR, empresa)
        assert usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.APROBAR, empresa)
        assert usuario.tiene_permiso(Modulos.PRODUCTOS, Acciones.VER, empresa)


    def test_vendedor_tiene_permisos_limitados(self, usuario, empresa):

        crear_relacion(usuario, empresa, RolUsuario.VENDEDOR)

        # Permitidos
        assert usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.VER, empresa)
        assert usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.CREAR, empresa)
        assert usuario.tiene_permiso(Modulos.PRODUCTOS, Acciones.VER, empresa)

        # NO Permitidos
        assert not usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.APROBAR, empresa)
        assert not usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.BORRAR, empresa)
        assert not usuario.tiene_permiso(Modulos.CONTACTOS, Acciones.ANULAR, empresa)


    def test_usuario_sin_relacion_no_tiene_permisos(self, usuario, empresa):

        # No se crea UserEmpresa
        assert not usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.CREAR, empresa)


    def test_usuario_con_relacion_inactiva_no_tiene_permisos(self, usuario, empresa):

        UserEmpresa.objects.create(
            user=usuario,
            empresa=empresa,
            rol=RolUsuario.ADMIN,
            activo=False
        )

        assert not usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.CREAR, empresa)


    def test_usuario_con_dos_empresas_distintos_roles(self, usuario, db):

        empresa_a = Empresa.objects.create(nombre="A", rut="1-9")
        empresa_b = Empresa.objects.create(nombre="B", rut="2-7")

        crear_relacion(usuario, empresa_a, RolUsuario.OWNER)
        crear_relacion(usuario, empresa_b, RolUsuario.VENDEDOR)

        # En A puede todo
        assert usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.BORRAR, empresa_a)

        # En B es limitado
        assert usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.CREAR, empresa_b)
        assert not usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.APROBAR, empresa_b)


    def test_vendedor_no_puede_aprobar_presupuesto(
        self,
        usuario_vendedor,
        empresa,
        presupuesto_borrador
    ):
        from apps.core.exceptions import AuthorizationError

        with pytest.raises(AuthorizationError):
            PresupuestoService.aprobar_presupuesto(
                presupuesto_borrador.id,
                empresa,
                usuario_vendedor
            )


    def test_usuario_no_puede_operar_en_empresa_ajena(
        self,
        usuario_owner_empresa_a,
        empresa_b,
        presupuesto_empresa_b
    ):
        from apps.core.exceptions import AuthorizationError

        with pytest.raises(AuthorizationError):
            PresupuestoService.aprobar_presupuesto(
                presupuesto_empresa_b.id,
                empresa_b,
                usuario_owner_empresa_a
            )


    def test_relacion_inactiva_bloquea_servicios(
        self,
        usuario_admin_inactivo,
        empresa,
        presupuesto_borrador
    ):
        from apps.core.exceptions import AuthorizationError

        with pytest.raises(AuthorizationError):
            PresupuestoService.aprobar_presupuesto(
                presupuesto_borrador.id,
                empresa,
                usuario_admin_inactivo
            )

    def test_usuario_roles_distintos_en_empresas(
        self,
        usuario,
        empresa,
        empresa_b,
        cliente,
        cliente_empresa_b,
        producto,
        empresa_activa
    ):
        empresa_activa(empresa)

        # Crear presupuestos
        presupuesto_a = Presupuesto.objects.create(
            empresa=empresa,
            cliente=cliente,
            numero=1,
            fecha=date.today(),
            estado=EstadoPresupuesto.BORRADOR,
            creado_por=usuario
        )

        presupuesto_b = Presupuesto.objects.create(
            empresa=empresa_b,
            cliente=cliente_empresa_b,
            numero=1,
            fecha=date.today(),
            estado=EstadoPresupuesto.BORRADOR,
            creado_por=usuario
        )

        # 🔥 Agregar item SOLO al presupuesto A
        PresupuestoItem.objects.create(
            presupuesto=presupuesto_a,
            producto=producto,
            cantidad=2,
            precio_unitario=producto.precio_referencia
        )

        # OWNER en A
        UserEmpresa.objects.create(
            user=usuario,
            empresa=empresa,
            rol=RolUsuario.OWNER,
            activo=True
        )

        # VENDEDOR en B
        UserEmpresa.objects.create(
            user=usuario,
            empresa=empresa_b,
            rol=RolUsuario.VENDEDOR,
            activo=True
        )

        # Puede aprobar en A
        PresupuestoService.aprobar_presupuesto(
            presupuesto_a.id,
            empresa,
            usuario
        )

        # No puede aprobar en B
        from apps.core.exceptions import AuthorizationError

        with pytest.raises(AuthorizationError):
            PresupuestoService.aprobar_presupuesto(
                presupuesto_b.id,
                empresa_b,
                usuario
            )

    def test_permiso_personalizado_habilita_accion_especifica(self, usuario, empresa):
        relacion = crear_relacion(usuario, empresa, RolUsuario.VENDEDOR)
        permiso = PermisoModulo.objects.create(
            nombre="Aprobar presupuesto",
            codigo="PRESUPUESTOS.APROBAR",
        )
        relacion.permisos.add(permiso)

        assert usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.APROBAR, empresa)
        assert not usuario.tiene_permiso(Modulos.PRESUPUESTOS, Acciones.BORRAR, empresa)

    def test_permiso_personalizado_por_modulo_wildcard(self, usuario, empresa):
        relacion = crear_relacion(usuario, empresa, RolUsuario.VENDEDOR)
        permiso = PermisoModulo.objects.create(
            nombre="Todos productos",
            codigo="PRODUCTOS.*",
        )
        relacion.permisos.add(permiso)

        assert usuario.tiene_permiso(Modulos.PRODUCTOS, Acciones.VER, empresa)
        assert usuario.tiene_permiso(Modulos.PRODUCTOS, Acciones.BORRAR, empresa)