import uuid
from django.db import models
from django.conf import settings

from ..tenant import get_current_empresa
from ..managers import EmpresaManager, AllObjectsManager


class BaseModel(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="%(class)s_registros"
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_creados"
    )
    all_objects = AllObjectsManager() # sin filtro
    objects = EmpresaManager()        # filtrado por tenant
    

    class Meta:
        abstract = True
        base_manager_name = 'all_objects'
    
    def save(self, *args, **kwargs):
    # 1. Si el registro ya existe en la DB (tiene Primary Key)
        if self.pk:
            # Usamos all_objects para bypass del filtro de tenant y verificar el dueño real
            original = self.__class__.all_objects.filter(pk=self.pk).values('empresa_id').first()
            if original and self.empresa_id and original['empresa_id'] != self.empresa_id:
                raise ValueError("No se puede transferir un registro entre empresas.")

        # 2. Si es nuevo y no viene con empresa, asignamos la del contexto
        if not self.empresa_id:
            current_empresa = get_current_empresa()
            if current_empresa is None:
                # Si eres superusuario creando desde el Admin, 
                # podrías querer elegir la empresa manualmente, 
                # así que solo lanzamos error si no se envió una.
                raise ValueError("Debes especificar una empresa o tener una sesión activa.")
            self.empresa = current_empresa

        super().save(*args, **kwargs)