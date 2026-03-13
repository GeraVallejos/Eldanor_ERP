from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0013_alter_documento_compra_bloquea_duplicado_nullable'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentocompraproveedor',
            name='tipo_documento',
            field=models.CharField(
                choices=[
                    ('GUIA_RECEPCION', 'Guía de recepción'),
                    ('FACTURA_COMPRA', 'Factura de compra'),
                    ('BOLETA_COMPRA', 'Boleta de compra'),
                ],
                max_length=20,
            ),
        ),
    ]
