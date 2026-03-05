from apps.core.tenant import set_current_empresa, set_current_user
from django.core.exceptions import ImproperlyConfigured, ValidationError

class TenantViewSetMixin:
    """
    Mixin multi-tenant profesional:
    - Setea contexto global
    - Filtra queryset por empresa activa
    - Autoasigna empresa al crear
    """

    def get_empresa(self):
        if hasattr(self.request, "_empresa_cache"):
            return self.request._empresa_cache

        user = self.request.user

        empresa = getattr(user, "empresa_activa", None)

        self.request._empresa_cache = empresa
        return empresa

    def _set_tenant_context(self):
        user = self.request.user
        empresa = self.get_empresa() if user and user.is_authenticated else None
        set_current_user(user if user and user.is_authenticated else None)
        set_current_empresa(empresa)

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return self.queryset.none()

        empresa = self.get_empresa()

        # Seteamos contexto global
        self._set_tenant_context()

        model = getattr(self, 'model', None)
        if not model:
            if not hasattr(self, "queryset"):
                raise ImproperlyConfigured(
                    "Debes definir 'queryset' o 'model' en el ViewSet."
                )
            model = self.queryset.model

        # Superuser puede ver todo
        if user.is_superuser:
            return model.all_objects.all()

        # 🔥 Aquí está la clave del multi-tenant
        if not empresa:
            return model.objects.none()

        return model.objects.filter(empresa=empresa)

    def perform_create(self, serializer):
        self._set_tenant_context()
        serializer.save()

    def perform_update(self, serializer):
        self._set_tenant_context()
        serializer.save()

    def perform_destroy(self, instance):
        self._set_tenant_context()
        instance.delete()

    
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
    

class TenantRelationValidationMixin:

    tenant_fk_fields = []

    def clean(self):
        super().clean()

        for field in self.tenant_fk_fields:
            related_obj = getattr(self, field, None)

            if related_obj and related_obj.empresa_id != self.empresa_id:
                raise ValidationError(
                    {field: f"El registro seleccionado de {field} no pertenece a su empresa."}
                )
