from django.db import models


class PlantillaPermisos(models.Model):
    codigo = models.CharField(max_length=60, unique=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    permisos = models.JSONField(default=list, blank=True)
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]

    def save(self, *args, **kwargs):
        self.codigo = (self.codigo or "").strip().upper()
        if self.permisos is None:
            self.permisos = []
        self.permisos = sorted(
            {
                str(codigo).strip().upper()
                for codigo in self.permisos
                if str(codigo).strip()
            }
        )
        super().save(*args, **kwargs)
