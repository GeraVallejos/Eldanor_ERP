from django.conf import settings
from django.db import models
from apps.core.permisos.permisoModulo import PermisoModulo
from django.db import models
from apps.core.roles import RolUsuario

class UserEmpresa(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="empresas_rel"
    )

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="usuarios_rel"
    )

    permisos = models.ManyToManyField(PermisoModulo, blank=True)

    rol = models.CharField(
        max_length=20,
        choices=RolUsuario.choices,
        default=RolUsuario.VENDEDOR
    )

    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "empresa"],
                name="unique_user_empresa"
            )
        ]

    def __str__(self):
        return f"{self.user.email} - {self.empresa.nombre} ({self.rol})"