from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from apps.core.models import UserEmpresa
from apps.core.api.serializer import (
    AplicarPlantillaSerializer,
    CambiarEmpresaActivaSerializer,
    EmpresaUsuarioSerializer,
    GestionPermisosSerializer,
    PlantillaPermisosSerializer,
    UsuarioEmpresaPermisosSerializer,
)
from apps.core.api.auth import CustomTokenObtainPairSerializer
from apps.core.permisos.constantes_permisos import Acciones, Modulos
from apps.core.permisos.plantillaPermisos import PlantillaPermisos
from apps.core.permisos.permisoModulo import PermisoModulo
from apps.core.permisos.services import (
    catalogo_permisos,
    permisos_efectivos_relacion,
    sincronizar_catalogo_permisos,
    sincronizar_plantillas_base,
    validar_codigos_permisos,
)


def _empresa_y_permiso_gestion(request):
    empresa = getattr(request.user, "empresa_activa", None)
    if not empresa:
        return None, Response({"detail": "No hay empresa activa."}, status=status.HTTP_400_BAD_REQUEST)

    if not request.user.tiene_permiso(Modulos.ADMINISTRACION, Acciones.GESTIONAR_PERMISOS, empresa):
        return None, Response({"detail": "No tiene permisos para gestionar permisos."}, status=status.HTTP_403_FORBIDDEN)

    return empresa, None


class EmpresasUsuarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        relaciones = UserEmpresa.objects.filter(
            user=request.user,
            activo=True
        ).select_related("empresa")

        empresas = [rel.empresa for rel in relaciones]

        serializer = EmpresaUsuarioSerializer(
            empresas,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data)
    

class CambiarEmpresaActivaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CambiarEmpresaActivaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        empresa_id = serializer.validated_data["empresa_id"]

        relacion = UserEmpresa.objects.filter(
            user=request.user,
            empresa_id=empresa_id,
            activo=True
        ).first()

        if not relacion:
            return Response(
                {"detail": "No tienes acceso a esta empresa."},
                status=status.HTTP_403_FORBIDDEN
            )

        request.user.empresa_activa = relacion.empresa
        request.user.save(update_fields=["empresa_activa"])

        return Response(
            {"detail": "Empresa activa cambiada correctamente."},
            status=status.HTTP_200_OK
        )


class CatalogoPermisosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sincronizar_catalogo_permisos()
        return Response(catalogo_permisos())


class MiembrosEmpresaPermisosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa, error = _empresa_y_permiso_gestion(request)
        if error:
            return error

        relaciones = (
            UserEmpresa.objects
            .filter(empresa=empresa, activo=True)
            .select_related("user")
            .prefetch_related("permisos")
            .order_by("user__email")
        )

        data = []
        for rel in relaciones:
            nombre = f"{rel.user.first_name} {rel.user.last_name}".strip() or rel.user.email
            personalizados = sorted(
                {
                    (p.codigo or "").strip().upper()
                    for p in rel.permisos.all()
                    if p.codigo
                }
            )
            data.append(
                {
                    "relacion_id": rel.id,
                    "user_id": rel.user_id,
                    "email": rel.user.email,
                    "nombre": nombre,
                    "rol": rel.rol,
                    "permisos_personalizados": personalizados,
                    "permisos_efectivos": permisos_efectivos_relacion(rel),
                }
            )

        return Response(UsuarioEmpresaPermisosSerializer(data, many=True).data)


class GestionPermisosUsuarioEmpresaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GestionPermisosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        empresa, error = _empresa_y_permiso_gestion(request)
        if error:
            return error

        sincronizar_catalogo_permisos()

        relacion = (
            UserEmpresa.objects
            .filter(
                id=serializer.validated_data["relacion_id"],
                empresa=empresa,
                activo=True,
            )
            .prefetch_related("permisos")
            .first()
        )

        if not relacion:
            return Response(
                {"detail": "Relación usuario-empresa no encontrada o inactiva."},
                status=status.HTTP_404_NOT_FOUND,
            )

        codigos, invalidos = validar_codigos_permisos(serializer.validated_data["permisos"])
        if invalidos:
            return Response(
                {"detail": "Existen códigos de permiso inválidos.", "invalidos": invalidos},
                status=status.HTTP_400_BAD_REQUEST,
            )

        permisos = list(PermisoModulo.objects.filter(codigo__in=codigos))
        codigos_encontrados = {p.codigo for p in permisos}

        relacion.permisos.set(permisos)

        return Response(
            {
                "detail": "Permisos actualizados correctamente.",
                "relacion_id": str(relacion.id),
                "permisos_personalizados": sorted(codigos_encontrados),
                "permisos_efectivos": permisos_efectivos_relacion(relacion),
            }
        )


class PlantillasPermisosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa, error = _empresa_y_permiso_gestion(request)
        if error:
            return error

        _ = empresa
        sincronizar_plantillas_base()
        plantillas = PlantillaPermisos.objects.filter(activa=True).order_by("nombre")
        data = [
            {
                "codigo": p.codigo,
                "nombre": p.nombre,
                "descripcion": p.descripcion,
                "permisos": p.permisos,
                "activa": p.activa,
            }
            for p in plantillas
        ]
        return Response(PlantillaPermisosSerializer(data, many=True).data)

    def post(self, request):
        empresa, error = _empresa_y_permiso_gestion(request)
        if error:
            return error

        _ = empresa
        serializer = PlantillaPermisosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        codigos, invalidos = validar_codigos_permisos(serializer.validated_data.get("permisos", []))
        if invalidos:
            return Response(
                {"detail": "Existen códigos de permiso inválidos.", "invalidos": invalidos},
                status=status.HTTP_400_BAD_REQUEST,
            )

        codigo = serializer.validated_data["codigo"].strip().upper()
        if PlantillaPermisos.objects.filter(codigo=codigo).exists():
            return Response(
                {"detail": "Ya existe una plantilla con ese código."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plantilla = PlantillaPermisos.objects.create(
            codigo=codigo,
            nombre=serializer.validated_data["nombre"],
            descripcion=serializer.validated_data.get("descripcion", ""),
            permisos=sorted(codigos),
            activa=serializer.validated_data.get("activa", True),
        )

        return Response(
            PlantillaPermisosSerializer(
                {
                    "codigo": plantilla.codigo,
                    "nombre": plantilla.nombre,
                    "descripcion": plantilla.descripcion,
                    "permisos": plantilla.permisos,
                    "activa": plantilla.activa,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )


class PlantillaPermisosDetalleView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, codigo):
        empresa, error = _empresa_y_permiso_gestion(request)
        if error:
            return error

        _ = empresa
        plantilla = PlantillaPermisos.objects.filter(codigo=codigo.upper()).first()
        if not plantilla:
            return Response({"detail": "Plantilla no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        data = {
            "codigo": plantilla.codigo,
            "nombre": plantilla.nombre,
            "descripcion": plantilla.descripcion,
            "permisos": plantilla.permisos,
            "activa": plantilla.activa,
        }
        data.update(request.data)

        serializer = PlantillaPermisosSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        codigos, invalidos = validar_codigos_permisos(serializer.validated_data.get("permisos", []))
        if invalidos:
            return Response(
                {"detail": "Existen códigos de permiso inválidos.", "invalidos": invalidos},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nuevo_codigo = serializer.validated_data["codigo"].strip().upper()
        duplicado = PlantillaPermisos.objects.filter(codigo=nuevo_codigo).exclude(id=plantilla.id).exists()
        if duplicado:
            return Response({"detail": "Ya existe una plantilla con ese código."}, status=status.HTTP_400_BAD_REQUEST)

        plantilla.codigo = nuevo_codigo
        plantilla.nombre = serializer.validated_data["nombre"]
        plantilla.descripcion = serializer.validated_data.get("descripcion", "")
        plantilla.permisos = sorted(codigos)
        plantilla.activa = serializer.validated_data.get("activa", plantilla.activa)
        plantilla.save()

        return Response(
            PlantillaPermisosSerializer(
                {
                    "codigo": plantilla.codigo,
                    "nombre": plantilla.nombre,
                    "descripcion": plantilla.descripcion,
                    "permisos": plantilla.permisos,
                    "activa": plantilla.activa,
                }
            ).data
        )


class AplicarPlantillaPermisosView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        empresa, error = _empresa_y_permiso_gestion(request)
        if error:
            return error

        sincronizar_plantillas_base()

        serializer = AplicarPlantillaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plantilla = PlantillaPermisos.objects.filter(
            codigo=serializer.validated_data["plantilla_codigo"].strip().upper(),
            activa=True,
        ).first()
        if not plantilla:
            return Response({"detail": "Plantilla no encontrada o inactiva."}, status=status.HTTP_404_NOT_FOUND)

        relacion = (
            UserEmpresa.objects
            .filter(
                id=serializer.validated_data["relacion_id"],
                empresa=empresa,
                activo=True,
            )
            .prefetch_related("permisos")
            .first()
        )
        if not relacion:
            return Response(
                {"detail": "Relación usuario-empresa no encontrada o inactiva."},
                status=status.HTTP_404_NOT_FOUND,
            )

        codigos, invalidos = validar_codigos_permisos(plantilla.permisos)
        if invalidos:
            return Response(
                {"detail": "La plantilla contiene permisos inválidos.", "invalidos": invalidos},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sincronizar_catalogo_permisos()
        permisos = list(PermisoModulo.objects.filter(codigo__in=codigos))
        relacion.permisos.set(permisos)

        return Response(
            {
                "detail": "Plantilla aplicada correctamente.",
                "relacion_id": relacion.id,
                "plantilla_codigo": plantilla.codigo,
                "permisos_personalizados": sorted(codigos),
                "permisos_efectivos": permisos_efectivos_relacion(relacion),
            }
        )
    
    
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer