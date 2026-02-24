from django.db import models
from .tenant import get_current_empresa


class EmpresaQuerySet(models.QuerySet):

    def for_current_empresa(self):
        empresa = get_current_empresa()
        if empresa is None:
            return self.none()
        return self.filter(empresa=empresa)


class EmpresaManager(models.Manager):

    def get_queryset(self):
        return EmpresaQuerySet(self.model, using=self._db).for_current_empresa()


class AllObjectsManager(models.Manager):
    """
    Manager sin filtro (solo para admin o procesos internos)
    """
    pass