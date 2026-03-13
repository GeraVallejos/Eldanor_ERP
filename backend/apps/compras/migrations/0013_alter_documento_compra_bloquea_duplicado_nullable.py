from django.db import migrations, models


def backfill_anulados_to_null(apps, schema_editor):
    DocumentoCompraProveedor = apps.get_model('compras', 'DocumentoCompraProveedor')
    DocumentoCompraProveedor._base_manager.filter(estado='ANULADO').update(bloquea_duplicado=None)


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0012_alter_ordencompraitem_descripcion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentocompraproveedor',
            name='bloquea_duplicado',
            field=models.BooleanField(default=True, editable=False, null=True),
        ),
        migrations.RunPython(backfill_anulados_to_null, migrations.RunPython.noop),
    ]
