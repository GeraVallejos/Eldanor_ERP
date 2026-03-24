from django.db import models

from apps.core.models import BaseModel


class ProductoSnapshot(BaseModel):
    """Snapshot inmutable del maestro de producto para versionado funcional."""

    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="snapshots_maestro",
    )
    producto_id_ref = models.UUIDField(db_index=True)
    version = models.PositiveIntegerField()
    event_type = models.CharField(max_length=120)
    changes = models.JSONField(default=dict, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-version", "-creado_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "producto_id_ref", "version"],
                name="uniq_producto_snapshot_version_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "producto_id_ref", "version"]),
            models.Index(fields=["empresa", "event_type", "creado_en"]),
        ]

    def __str__(self):
        return f"Snapshot producto {self.producto_id_ref} v{self.version}"
