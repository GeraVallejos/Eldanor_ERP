from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("compras", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="recepcioncompra",
            name="orden_compra",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="recepciones",
                to="compras.ordencompra",
            ),
        ),
        migrations.AlterField(
            model_name="recepcioncompraitem",
            name="orden_item",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="recepciones",
                to="compras.ordencompraitem",
            ),
        ),
        migrations.AddField(
            model_name="recepcioncompraitem",
            name="precio_unitario",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14),
        ),
    ]
