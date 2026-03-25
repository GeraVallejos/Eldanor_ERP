from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("productos", "0009_rename_productos_p_empresa_79dbf7_idx_productos_p_empresa_7f984d_idx_and_more"),
        ("inventario", "0006_alter_movimientoinventario_documento_tipo_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AjusteInventarioMasivo",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("estado", models.CharField(max_length=20)),
                ("observaciones", models.TextField(blank=True)),
                ("subtotal", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("total", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("numero", models.CharField(max_length=50)),
                ("referencia", models.CharField(max_length=150)),
                ("motivo", models.CharField(max_length=120)),
                ("confirmado_en", models.DateTimeField(auto_now_add=True)),
                ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_creados", to=settings.AUTH_USER_MODEL)),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_registros", to="core.empresa")),
            ],
            options={
                "ordering": ["-creado_en", "-id"],
                "indexes": [
                    models.Index(fields=["empresa", "estado"], name="inventario_a_empresa_85ff68_idx"),
                    models.Index(fields=["empresa", "numero"], name="inventario_a_empresa_74ba9f_idx"),
                    models.Index(fields=["empresa", "confirmado_en"], name="inventario_a_empresa_529416_idx"),
                ],
                "base_manager_name": "all_objects",
            },
        ),
        migrations.CreateModel(
            name="TrasladoInventarioMasivo",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("estado", models.CharField(max_length=20)),
                ("observaciones", models.TextField(blank=True)),
                ("subtotal", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("total", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("numero", models.CharField(max_length=50)),
                ("referencia", models.CharField(max_length=150)),
                ("motivo", models.CharField(max_length=120)),
                ("confirmado_en", models.DateTimeField(auto_now_add=True)),
                ("bodega_destino", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="traslados_masivos_destino", to="inventario.bodega")),
                ("bodega_origen", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="traslados_masivos_origen", to="inventario.bodega")),
                ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_creados", to=settings.AUTH_USER_MODEL)),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_registros", to="core.empresa")),
            ],
            options={
                "ordering": ["-creado_en", "-id"],
                "indexes": [
                    models.Index(fields=["empresa", "estado"], name="inventario_t_empresa_1aa8f0_idx"),
                    models.Index(fields=["empresa", "numero"], name="inventario_t_empresa_57a715_idx"),
                    models.Index(fields=["empresa", "confirmado_en"], name="inventario_t_empresa_35c62b_idx"),
                ],
                "base_manager_name": "all_objects",
            },
        ),
        migrations.CreateModel(
            name="AjusteInventarioMasivoItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("stock_objetivo", models.DecimalField(decimal_places=2, max_digits=12)),
                ("stock_actual", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("diferencia", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("bodega", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ajustes_masivos", to="inventario.bodega")),
                ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_creados", to=settings.AUTH_USER_MODEL)),
                ("documento", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="inventario.ajusteinventariomasivo")),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_registros", to="core.empresa")),
                ("movimiento", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ajustes_masivos_items", to="inventario.movimientoinventario")),
                ("producto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ajustes_masivos", to="productos.producto")),
            ],
            options={
                "ordering": ["creado_en", "id"],
                "indexes": [
                    models.Index(fields=["empresa", "documento"], name="inventario_a_empresa_4feea4_idx"),
                    models.Index(fields=["empresa", "producto"], name="inventario_a_empresa_645804_idx"),
                ],
                "base_manager_name": "all_objects",
            },
        ),
        migrations.CreateModel(
            name="TrasladoInventarioMasivoItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("cantidad", models.DecimalField(decimal_places=2, max_digits=12)),
                ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_creados", to=settings.AUTH_USER_MODEL)),
                ("documento", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="inventario.trasladoinventariomasivo")),
                ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_registros", to="core.empresa")),
                ("movimiento_entrada", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="traslados_masivos_entrada_items", to="inventario.movimientoinventario")),
                ("movimiento_salida", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="traslados_masivos_salida_items", to="inventario.movimientoinventario")),
                ("producto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="traslados_masivos", to="productos.producto")),
            ],
            options={
                "ordering": ["creado_en", "id"],
                "indexes": [
                    models.Index(fields=["empresa", "documento"], name="inventario_t_empresa_476503_idx"),
                    models.Index(fields=["empresa", "producto"], name="inventario_t_empresa_e6b16f_idx"),
                ],
                "base_manager_name": "all_objects",
            },
        ),
    ]
