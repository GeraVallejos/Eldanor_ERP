import uuid
from django.db import models
from django.conf import settings

from ..tenant import get_current_empresa, get_current_user
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
    # 1. Usamos _state.adding para detectar si es CREACIÓN
        if self._state.adding:
            # Asignar Empresa
            if not self.empresa_id:
                curr_empresa = get_current_empresa()
                if curr_empresa:
                    self.empresa = curr_empresa
                else:
                    # Si no hay empresa en el contexto Y no se pasó manualmente, error
                    if not getattr(self, 'empresa', None):
                        raise ValueError("No hay empresa activa en el contexto.")

            # Asignar Creador automáticamente
            if not self.creado_por_id:
                curr_user = get_current_user()
                if curr_user:
                    self.creado_por = curr_user

        # 2. Lógica para EDICIÓN (el objeto ya existe en la base de datos)
        else:
            # Verificamos si empresa_id cambió comparando con la DB
            # Solo hacemos la consulta si empresa_id está presente en la instancia actual
            if self.empresa_id:
                original_empresa_id = self.__class__.all_objects.filter(pk=self.pk).values_list('empresa_id', flat=True).first()
                if original_empresa_id and str(original_empresa_id) != str(self.empresa_id):
                    raise ValueError("La empresa propietaria no puede ser modificada.")
                
        skip_clean = kwargs.pop('skip_clean', False)
    
        if not skip_clean:
            self.full_clean()

        super().save(*args, **kwargs)