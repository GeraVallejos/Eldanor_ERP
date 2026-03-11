from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("compras", "0005_unique_doc_compra_activo_por_oc"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="documentocompraproveedor",
            name="unique_doc_compra_activo_por_oc",
        ),
    ]
