from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("compras", "0006_remove_unique_doc_compra_activo_por_oc"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="documentocompraproveedor",
            constraint=models.UniqueConstraint(
                fields=("empresa", "proveedor", "tipo_documento", "folio", "serie"),
                condition=~Q(estado="ANULADO"),
                name="uniq_doc_compra_emp_prov_tipo_folio_serie",
            ),
        ),
    ]
