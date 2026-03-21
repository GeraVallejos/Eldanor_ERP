from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("compras", "0017_alter_documentocompraproveedor_estado_contable_and_more"),
        ("tesoreria", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="documentocompraproveedor",
                    name="moneda",
                    field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name="documentos_compra", to="tesoreria.moneda"),
                ),
            ],
        ),
    ]
