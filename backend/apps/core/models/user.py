import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.core.validators import normalizar_texto
from apps.core.permisos.constantes_permisos import PERMISOS_POR_ROL, ALL


class User(AbstractUser):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    email = models.EmailField(unique=True)

    empresa_activa = models.ForeignKey(
        "core.Empresa",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    telefono = models.CharField(max_length=20, blank=True)

    activo = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['username']

    def save(self, *args, **kwargs):
        # 1. Email a minúsculas (fundamental para evitar duplicados por error de tipeo)
        if self.email:
            self.email = normalizar_texto(self.email, es_email=True)
        
        # 2. Forzar que el username sea igual al email si no se usa
        if not self.username:
            self.username = self.email

        # 3. Nombres y Apellidos en MAYÚSCULAS
        if self.first_name:
            self.first_name = normalizar_texto(self.first_name)
        if self.last_name:
            self.last_name = normalizar_texto(self.last_name)

        super().save(*args, **kwargs)

    def get_rol_en_empresa(self, empresa):
        relacion = self.empresas_rel.filter(
            empresa=empresa,
            activo=True
        ).first()

        if not relacion:
            return None

        return relacion.rol
    
    def tiene_permiso(self, modulo, accion, empresa):

        rol = self.get_rol_en_empresa(empresa)

        if not rol:
            return False

        permisos = PERMISOS_POR_ROL.get(rol)

        # OWNER absoluto
        if permisos is ALL:
            return True

        if not permisos:
            return False

        acciones_permitidas = permisos.get(modulo, [])

        return accion in acciones_permitidas

    def __str__(self):
        # Una representación más amigable para el Admin
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.email})"
        return self.email