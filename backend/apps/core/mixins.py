from apps.core.tenant import set_current_empresa, set_current_user

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