from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.core.models import UserEmpresa


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user

        relaciones = UserEmpresa.objects.filter(
            user=user,
            activo=True
        )

        if relaciones.count() == 1 and not user.empresa_activa:
            user.empresa_activa = relaciones.first().empresa
            user.save(update_fields=["empresa_activa"])

        return data