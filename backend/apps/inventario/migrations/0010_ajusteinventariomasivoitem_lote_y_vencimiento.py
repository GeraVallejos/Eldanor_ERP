from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0009_merge_20260327_0001"),
    ]

    operations = [
        migrations.AddField(
            model_name="ajusteinventariomasivoitem",
            name="fecha_vencimiento",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ajusteinventariomasivoitem",
            name="lote_codigo",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
    ]
