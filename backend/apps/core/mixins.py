from apps.core.tenant import set_current_empresa, set_current_user
import json
from django.core.serializers.json import DjangoJSONEncoder

class TenantViewSetMixin:
    """
    Mixin integral para ViewSets que:
    1. Filtra los datos por la empresa del usuario (Multi-tenancy).
    2. Setea el contexto global para los Managers de Django.
    3. Asigna automáticamente Empresa y Creador al guardar.
    """
    
    def get_queryset(self):
        user = self.request.user
        # Aseguramos que el contexto esté seteado incluso si el middleware se salta
        if user.is_authenticated:
            set_current_user(user)
            set_current_empresa(getattr(user, 'empresa', None))

        # Es mejor usar self.get_model() o acceder vía queryset original para ser más robusto
        model = getattr(self, 'model', None) or self.queryset.model
        
        if user.is_superuser:
            return model.all_objects.all()
        
        return model.objects.all()

    def perform_create(self, serializer):
        """
        Al crear un nuevo registro (POST), inyectamos la empresa 
        y el usuario creador automáticamente.
        """
        # Obtenemos los datos del request actual
        user = self.request.user
        empresa = getattr(user, 'empresa', None)

        # Guardamos el objeto pasando los campos automáticos.
        # Esto sobrescribe cualquier valor enviado maliciosamente desde el front.
        serializer.save(
            empresa=empresa,
            creado_por=user
        )

    def perform_update(self, serializer):
        """
        Opcional: Aseguramos que durante un PUT/PATCH no se cambie 
        la empresa accidentalmente.
        """
        serializer.save(empresa=getattr(self.request.user, 'empresa', None))

    
class AuditDiffMixin:
    """
    Mixin para comparar cambios en el modelo.
    """
    def get_dirty_fields(self):
        if not self.pk:
            return {}
        
        # Obtenemos la versión actual de la DB
        original = self.__class__.all_objects.get(pk=self.pk)
        dirty = {}
        
        # Campos a ignorar en la auditoría
        ignored_fields = ['actualizado_en']

        for field in self._meta.fields:
            if field.name in ignored_fields:
                continue
                
            field_name = field.name
            current_value = getattr(self, field_name)
            original_value = getattr(original, field_name)

            if current_value != original_value:
                # Guardamos como string para evitar problemas de serialización
                dirty[field_name] = {
                    'antes': str(original_value),
                    'despues': str(current_value)
                }
        return dirty