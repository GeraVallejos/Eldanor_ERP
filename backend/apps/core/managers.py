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
        
        # 3. Si el usuario está en el contextvar y tiene empresa asignada, filtramos por esa empresa
        if user and hasattr(user, 'empresa') and user.empresa:
            return self.filter(empresa=user.empresa)

        # 4. Sin empresa ni usuario válido, devolvemos un queryset vacío para evitar fugas de datos
        return self.none()


class EmpresaManager(models.Manager):

    def get_queryset(self):
        return EmpresaQuerySet(self.model, using=self._db).for_current_empresa()


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        # Usamos models.QuerySet directamente para saltarnos EmpresaQuerySet
        return models.QuerySet(self.model, using=self._db)