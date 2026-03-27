from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0007_documentos_masivos_inventario"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ajusteinventariomasivo",
            name="confirmado_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="trasladoinventariomasivo",
            name="confirmado_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
