from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("compras", "0004_correccion_documento_compra"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="documentocompraproveedor",
            constraint=models.UniqueConstraint(
                fields=("empresa", "orden_compra"),
                condition=Q(orden_compra__isnull=False) & ~Q(estado="ANULADO"),
                name="unique_doc_compra_activo_por_oc",
            ),
        ),
    ]
