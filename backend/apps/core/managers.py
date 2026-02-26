from django.db import models
from .tenant import get_current_empresa


class EmpresaQuerySet(models.QuerySet):
    def for_current_empresa(self):
        from .tenant import get_current_empresa, get_current_user
        
        empresa = get_current_empresa()
        user = get_current_user()

        # 1. Si es superusuario, libertad total
        if user and user.is_superuser:
            return self

        # 2. Si la empresa está en el contextvar (Middleware API)
        if empresa:
            return self.filter(empresa=empresa)
        
        # 3. Salvavidas (Contexto manual)
        if user and hasattr(user, 'empresa') and user.empresa:
            return self.filter(empresa=user.empresa)

        # 4. CAMBIO CLAVE: 
        # Si no hay usuario ni empresa en el contexto (CASO DJANGO ADMIN),
        # devolvemos el queryset completo SIN filtrar.
        # De esta forma, el TenantAdminMixin puede aplicar su propio filtro:
        # .filter(empresa=request.user.empresa) sin que el Manager lo bloquee.
        return self


class EmpresaManager(models.Manager):

    def get_queryset(self):
        return EmpresaQuerySet(self.model, using=self._db).for_current_empresa()


class AllObjectsManager(models.Manager):
    """
    Manager sin filtro (solo para admin o procesos internos)
    """
    pass