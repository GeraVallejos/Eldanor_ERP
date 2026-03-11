from django.conf import settings
import mimetypes
from django.middleware.csrf import get_token
from django.utils.module_loading import import_string
from django.http import HttpResponse
from io import BytesIO
from PIL import Image
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from apps.core.models import Empresa, UserEmpresa
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


def _auth_cookie_kwargs(max_age):
    return {
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "domain": settings.AUTH_COOKIE_DOMAIN,
        "path": settings.AUTH_COOKIE_PATH,
        "max_age": max_age,
    }


def _set_auth_cookies(response, access_token, refresh_token=None):
    access_seconds = int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds())
    response.set_cookie(
        settings.AUTH_COOKIE_ACCESS_NAME,
        access_token,
        **_auth_cookie_kwargs(access_seconds),
    )

    if refresh_token:
        refresh_seconds = int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds())
        response.set_cookie(
            settings.AUTH_COOKIE_REFRESH_NAME,
            refresh_token,
            **_auth_cookie_kwargs(refresh_seconds),
        )


def _clear_auth_cookies(response):
    response.delete_cookie(
        settings.AUTH_COOKIE_ACCESS_NAME,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path=settings.AUTH_COOKIE_PATH,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        settings.AUTH_COOKIE_REFRESH_NAME,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path=settings.AUTH_COOKIE_PATH,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def _ensure_csrf_cookie(request, response):
    # Generate and attach csrf cookie so SPA can send X-CSRFToken on unsafe methods.
    get_token(request)
    return response


def _serialize_user(user, request=None):
    empresa = getattr(user, "empresa_activa", None)
    empresa_logo = None
    relacion_activa = None
    permisos = []
    rol = None

    if empresa and getattr(empresa, "logo", None):
        try:
            logo_url = empresa.logo.url
            empresa_logo = request.build_absolute_uri(logo_url) if request else logo_url
        except Exception:
            empresa_logo = None

    if empresa:
        relacion_activa = (
            UserEmpresa.objects
            .filter(user=user, empresa=empresa, activo=True)
            .prefetch_related("permisos")
            .first()
        )

    if user.is_superuser:
        rol = "SUPERUSER"
        permisos = ["*"]
    elif relacion_activa:
        rol = relacion_activa.rol
        permisos = permisos_efectivos_relacion(relacion_activa)

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "empresa_id": getattr(empresa, "id", None),
        "empresa_nombre": getattr(empresa, "nombre", None),
        "empresa_logo": empresa_logo,
        "rol": rol,
        "permissions": permisos,
    }


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
        if request.user.is_superuser:
            empresas = list(Empresa.objects.order_by("nombre"))
        else:
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

        if request.user.is_superuser:
            empresa = Empresa.objects.filter(id=empresa_id).first()
            if not empresa:
                return Response(
                    {"detail": "Empresa no encontrada."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            request.user.empresa_activa = empresa
        else:
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

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0])

        data = serializer.validated_data
        access_token = data.get("access")
        refresh_token = data.get("refresh")

        response = Response(
            {
                "detail": "Inicio de sesion exitoso.",
                "user": _serialize_user(serializer.user, request=request),
            },
            status=status.HTTP_200_OK,
        )

        if access_token:
            _set_auth_cookies(response, access_token, refresh_token)

        return _ensure_csrf_cookie(request, response)


class CustomTokenRefreshView(APIView):
    permission_classes = []

    def post(self, request):
        refresh_token = request.data.get("refresh") or request.COOKIES.get(settings.AUTH_COOKIE_REFRESH_NAME)

        if not refresh_token:
            return Response(
                {"detail": "Refresh token no proporcionado."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer_class = import_string(api_settings.TOKEN_REFRESH_SERIALIZER)
        serializer = serializer_class(data={"refresh": refresh_token})

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0])

        data = serializer.validated_data
        response = Response({"detail": "Sesion renovada."}, status=status.HTTP_200_OK)
        _set_auth_cookies(response, data.get("access"), data.get("refresh"))
        return _ensure_csrf_cookie(request, response)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = Response(
            {"user": _serialize_user(request.user, request=request)},
            status=status.HTTP_200_OK,
        )
        return _ensure_csrf_cookie(request, response)


class LogoutView(APIView):
    permission_classes = []

    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_auth_cookies(response)
        return response


class EmpresaLogoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = getattr(request.user, "empresa_activa", None)
        if not empresa or not getattr(empresa, "logo", None):
            return Response({"detail": "La empresa activa no tiene logo."}, status=status.HTTP_404_NOT_FOUND)

        try:
            empresa.logo.open("rb")
            content = empresa.logo.read()
            empresa.logo.close()
        except Exception:
            return Response({"detail": "No se pudo cargar el logo de la empresa."}, status=status.HTTP_404_NOT_FOUND)

        content_type = mimetypes.guess_type(empresa.logo.name or "")[0] or "application/octet-stream"

        # Para documentos PDF normalizamos a PNG (webp puede no renderizarse en @react-pdf/renderer).
        try:
            with Image.open(BytesIO(content)) as img:
                has_alpha = img.mode in ("RGBA", "LA") or (
                    img.mode == "P" and "transparency" in img.info
                )
                normalized = img.convert("RGBA" if has_alpha else "RGB")

                buffer = BytesIO()
                normalized.save(buffer, format="PNG", optimize=True)
                content = buffer.getvalue()
                content_type = "image/png"
        except Exception:
            pass

        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = 'inline; filename="empresa-logo.png"'
        response["Cache-Control"] = "private, max-age=300"
        return response