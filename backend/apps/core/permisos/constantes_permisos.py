from apps.core.roles import RolUsuario


ALL = object()

class Modulos:
    PRESUPUESTOS = "PRESUPUESTOS"
    PRODUCTOS = "PRODUCTOS"
    CONTACTOS = "CONTACTOS"


class Acciones:
    VER = "VER"
    CREAR = "CREAR"
    EDITAR = "EDITAR"
    APROBAR = "APROBAR"
    ANULAR = "ANULAR"
    BORRAR = "BORRAR"




PERMISOS_POR_ROL = {
    RolUsuario.OWNER: ALL,
    RolUsuario.ADMIN: ALL,
    RolUsuario.VENDEDOR: {
        Modulos.PRESUPUESTOS: [Acciones.VER, Acciones.CREAR],
        Modulos.PRODUCTOS: [Acciones.VER],
        Modulos.CONTACTOS: [Acciones.VER, Acciones.CREAR],
    },
}
