from apps.core.roles import RolUsuario


ALL = object()

class Modulos:
    PRESUPUESTOS = "PRESUPUESTOS"
    PRODUCTOS = "PRODUCTOS"
    CONTACTOS = "CONTACTOS"
    AUDITORIA = "AUDITORIA"
    INVENTARIO = "INVENTARIO"
    ADMINISTRACION = "ADMINISTRACION"
    VENTAS = "VENTAS"
    FACTURACION = "FACTURACION"
    COMPRAS = "COMPRAS"
    TESORERIA = "TESORERIA"
    CONTABILIDAD = "CONTABILIDAD"


class Acciones:
    VER = "VER"
    CREAR = "CREAR"
    EDITAR = "EDITAR"
    APROBAR = "APROBAR"
    ANULAR = "ANULAR"
    BORRAR = "BORRAR"
    EMITIR = "EMITIR"
    COBRAR = "COBRAR"
    PAGAR = "PAGAR"
    CONCILIAR = "CONCILIAR"
    CONTABILIZAR = "CONTABILIZAR"
    GESTIONAR_PERMISOS = "GESTIONAR_PERMISOS"


PERMISOS_CATALOGO = {
    Modulos.PRESUPUESTOS: [
        Acciones.VER,
        Acciones.CREAR,
        Acciones.EDITAR,
        Acciones.APROBAR,
        Acciones.ANULAR,
        Acciones.BORRAR,
    ],
    Modulos.PRODUCTOS: [
        Acciones.VER,
        Acciones.CREAR,
        Acciones.EDITAR,
        Acciones.BORRAR,
    ],
    Modulos.INVENTARIO: [
        Acciones.VER,
        Acciones.CREAR,
        Acciones.EDITAR,
        Acciones.BORRAR,
    ],
    Modulos.CONTACTOS: [
        Acciones.VER,
        Acciones.CREAR,
        Acciones.EDITAR,
        Acciones.BORRAR,
    ],
    Modulos.AUDITORIA: [
        Acciones.VER,
    ],
    Modulos.ADMINISTRACION: [
        Acciones.VER,
        Acciones.GESTIONAR_PERMISOS,
    ],
    Modulos.VENTAS: [
        Acciones.VER,
        Acciones.CREAR,
        Acciones.EDITAR,
        Acciones.APROBAR,
        Acciones.ANULAR,
        Acciones.BORRAR,
    ],
    Modulos.FACTURACION: [
        Acciones.VER,
        Acciones.CREAR,
        Acciones.EDITAR,
        Acciones.EMITIR,
        Acciones.ANULAR,
    ],
    Modulos.COMPRAS: [
        Acciones.VER,
        Acciones.CREAR,
        Acciones.EDITAR,
        Acciones.APROBAR,
        Acciones.ANULAR,
    ],
    Modulos.TESORERIA: [
        Acciones.VER,
        Acciones.COBRAR,
        Acciones.PAGAR,
        Acciones.CONCILIAR,
    ],
    Modulos.CONTABILIDAD: [
        Acciones.VER,
        Acciones.CONTABILIZAR,
    ],
}


def generar_codigos_catalogo():
    codigos = []
    for modulo, acciones in PERMISOS_CATALOGO.items():
        codigos.append(f"{modulo}.*")
        for accion in acciones:
            codigos.append(f"{modulo}.{accion}")
    codigos.append("*")
    return codigos




PERMISOS_POR_ROL = {
    RolUsuario.OWNER: ALL,
    RolUsuario.ADMIN: ALL,
    RolUsuario.VENDEDOR: {
        Modulos.PRESUPUESTOS: [Acciones.VER, Acciones.CREAR],
        Modulos.PRODUCTOS: [Acciones.VER],
        Modulos.CONTACTOS: [Acciones.VER, Acciones.CREAR],
        Modulos.VENTAS: [Acciones.VER, Acciones.CREAR],
        Modulos.FACTURACION: [Acciones.VER],
    },
}
