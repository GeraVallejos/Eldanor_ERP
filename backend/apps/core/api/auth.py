from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.core.models import UserEmpresa


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user

        relaciones = UserEmpresa.objects.filter(
            user=user,
            activo=True
        ).select_related('empresa')

        if not relaciones.exists():
            return data

        empresa_actual_valida = (
            user.empresa_activa
            and relaciones.filter(empresa=user.empresa_activa).exists()
        )

        if not empresa_actual_valida:
            user.empresa_activa = relaciones.first().empresa
            user.save(update_fields=["empresa_activa"])

        return data