from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("productos", "0006_producto_usa_series_listaprecio_listaprecioitem_and_more"),
        ("tesoreria", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="producto",
                    name="moneda",
                    field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name="productos", to="tesoreria.moneda"),
                ),
                migrations.AlterField(
                    model_name="listaprecio",
                    name="moneda",
                    field=models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="listas_precio", to="tesoreria.moneda"),
                ),
            ],
        ),
    ]
