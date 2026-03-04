from django.db import models
from apps.core.models import BaseModel


class PresupuestoHistorial(BaseModel):
    presupuesto = models.ForeignKey(
        "Presupuesto", on_delete=models.CASCADE, related_name="historial"
    )
    usuario = models.ForeignKey("core.User", on_delete=models.PROTECT)
    estado_anterior = models.CharField(max_length=20)
    estado_nuevo = models.CharField(max_length=20)
    motivo = models.TextField(blank=True)
    cambios = models.JSONField(null=True, blank=True)

    class Meta:
        pass