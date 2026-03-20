from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("presupuestos", "0005_alter_presupuestoitem_descripcion"),
        ("ventas", "0004_alter_facturaventa_estado_contable_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedidoventa",
            name="presupuesto_origen",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pedidos_venta_generados",
                to="presupuestos.presupuesto",
            ),
        ),
        migrations.AddField(
            model_name="facturaventa",
            name="presupuesto_origen",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="facturas_venta_generadas",
                to="presupuestos.presupuesto",
            ),
        ),
        migrations.AddIndex(
            model_name="pedidoventa",
            index=models.Index(fields=["empresa", "presupuesto_origen"], name="ventas_pedi_empresa_25e884_idx"),
        ),
        migrations.AddIndex(
            model_name="facturaventa",
            index=models.Index(fields=["empresa", "presupuesto_origen"], name="ventas_fact_empresa_4089e3_idx"),
        ),
    ]
