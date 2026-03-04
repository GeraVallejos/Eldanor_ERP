from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from apps.core.models import UserEmpresa
from apps.core.api.serializer import CambiarEmpresaActivaSerializer, EmpresaUsuarioSerializer
from apps.core.api.auth import CustomTokenObtainPairSerializer


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
    
    
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer