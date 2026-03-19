from apps.core.permisos.constantes_permisos import (
    ALL,
    PERMISOS_CATALOGO,
    PERMISOS_POR_ROL,
    generar_codigos_catalogo,
)
from apps.core.permisos.plantillaPermisos import PlantillaPermisos
from apps.core.permisos.permisoModulo import PermisoModulo


PLANTILLAS_BASE = [
    {
        "codigo": "VENTAS_BASE",
        "nombre": "Ventas Base",
        "descripcion": "Operación comercial diaria sin administración avanzada.",
        "permisos": [
            "PRESUPUESTOS.VER",
            "PRESUPUESTOS.CREAR",
            "CONTACTOS.VER",
            "CONTACTOS.CREAR",
            "PRODUCTOS.VER",
            "VENTAS.VER",
            "VENTAS.CREAR",
            "FACTURACION.VER",
        ],
    },
    {
        "codigo": "FINANZAS_BASE",
        "nombre": "Finanzas Base",
        "descripcion": "Gestión de cobros, pagos y operaciones contables básicas.",
        "permisos": [
            "TESORERIA.VER",
            "TESORERIA.COBRAR",
            "TESORERIA.PAGAR",
            "TESORERIA.CONCILIAR",
            "CONTABILIDAD.VER",
            "CONTABILIDAD.CONTABILIZAR",
            "FACTURACION.VER",
            "FACTURACION.EMITIR",
        ],
    },
    {
        "codigo": "COMPRAS_BASE",
        "nombre": "Compras Base",
        "descripcion": "Flujo de abastecimiento y aprobaciones operativas de compras.",
        "permisos": [
            "COMPRAS.VER",
            "COMPRAS.CREAR",
            "COMPRAS.EDITAR",
            "COMPRAS.APROBAR",
            "PRODUCTOS.VER",
            "CONTACTOS.VER",
        ],
    },
]


def sincronizar_catalogo_permisos():
    """Asegura que el catálogo mínimo exista en la base de datos."""
    codigos = generar_codigos_catalogo()
    for codigo in codigos:
        nombre = codigo.replace(".", " ").replace("_", " ").title()
        PermisoModulo.objects.get_or_create(
            codigo=codigo,
            defaults={"nombre": nombre},
        )


def codigos_permitidos_set():
    return {codigo.upper() for codigo in generar_codigos_catalogo()}


def validar_codigos_permisos(codigos):
    normalizados = {
        str(codigo).strip().upper()
        for codigo in codigos
        if str(codigo).strip()
    }
    permitidos = codigos_permitidos_set()
    invalidos = sorted(normalizados - permitidos)
    return normalizados, invalidos


def permisos_efectivos_relacion(relacion):
    """
    Devuelve permisos efectivos para mostrar en API.
    Si hay permisos personalizados, usa esos; si no, aplica rol.
    """
    if relacion.rol in {"OWNER", "ADMIN"}:
        return ["*"]

    personalizados = sorted(
        {
            (p.codigo or "").strip().upper()
            for p in relacion.permisos.all()
            if p.codigo
        }
    )

    if personalizados:
        return personalizados

    permisos_rol = PERMISOS_POR_ROL.get(relacion.rol)
    if permisos_rol is ALL:
        return ["*"]

    if not permisos_rol:
        return []

    efectivos = []
    for modulo, acciones in permisos_rol.items():
        for accion in acciones:
            efectivos.append(f"{modulo}.{accion}")
    return sorted(set(efectivos))


def catalogo_permisos():
    """Estructura estable para front: módulo -> acciones disponibles."""
    return PERMISOS_CATALOGO


def sincronizar_plantillas_base():
    sincronizar_catalogo_permisos()
    permitidos = codigos_permitidos_set()
    for plantilla in PLANTILLAS_BASE:
        permisos = sorted(
            {
                codigo for codigo in plantilla["permisos"]
                if codigo in permitidos
            }
        )
        PlantillaPermisos.objects.get_or_create(
            codigo=plantilla["codigo"],
            defaults={
                "nombre": plantilla["nombre"],
                "descripcion": plantilla.get("descripcion", ""),
                "permisos": permisos,
                "activa": True,
            },
        )
