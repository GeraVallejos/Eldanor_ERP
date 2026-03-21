import django.db.models.deletion
import django.db.models.manager
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0016_cuentabancariaempresa_movimientobancario_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="ConfiguracionTributaria",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("creado_en", models.DateTimeField(auto_now_add=True)),
                        ("actualizado_en", models.DateTimeField(auto_now=True)),
                        ("ambiente", models.CharField(choices=[("CERTIFICACION", "Certificacion"), ("PRODUCCION", "Produccion")], default="CERTIFICACION", max_length=20)),
                        ("rut_emisor", models.CharField(max_length=12)),
                        ("razon_social", models.CharField(max_length=200)),
                        ("certificado_alias", models.CharField(blank=True, max_length=150)),
                        ("certificado_activo", models.BooleanField(default=False)),
                        ("resolucion_numero", models.PositiveIntegerField(blank=True, null=True)),
                        ("resolucion_fecha", models.DateField(blank=True, null=True)),
                        ("email_intercambio_dte", models.EmailField(blank=True, max_length=254)),
                        ("proveedor_envio", models.CharField(blank=True, max_length=80)),
                        ("activa", models.BooleanField(default=True)),
                        ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_creados", to=settings.AUTH_USER_MODEL)),
                        ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_registros", to="core.empresa")),
                    ],
                    options={
                        "db_table": "core_configuraciontributaria",
                        "indexes": [models.Index(fields=["empresa", "activa"], name="core_config_empresa_16c229_idx")],
                        "constraints": [models.UniqueConstraint(fields=("empresa",), name="unique_configuracion_tributaria_por_empresa")],
                    },
                    managers=[
                        ("all_objects", django.db.models.manager.Manager()),
                    ],
                ),
                migrations.CreateModel(
                    name="RangoFolioTributario",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("creado_en", models.DateTimeField(auto_now_add=True)),
                        ("actualizado_en", models.DateTimeField(auto_now=True)),
                        ("tipo_documento", models.CharField(choices=[("FACTURA_VENTA", "Factura de venta"), ("GUIA_DESPACHO", "Guia de despacho"), ("NOTA_CREDITO_VENTA", "Nota de credito de venta")], max_length=40)),
                        ("caf_nombre", models.CharField(max_length=120)),
                        ("folio_desde", models.PositiveIntegerField()),
                        ("folio_hasta", models.PositiveIntegerField()),
                        ("folio_actual", models.PositiveIntegerField(blank=True, null=True)),
                        ("fecha_autorizacion", models.DateField(blank=True, null=True)),
                        ("fecha_vencimiento", models.DateField(blank=True, null=True)),
                        ("activo", models.BooleanField(default=True)),
                        ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_creados", to=settings.AUTH_USER_MODEL)),
                        ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_registros", to="core.empresa")),
                    ],
                    options={
                        "db_table": "core_rangofoliotributario",
                        "indexes": [
                            models.Index(fields=["empresa", "tipo_documento", "activo"], name="core_rangof_empresa_8c589a_idx"),
                            models.Index(fields=["empresa", "fecha_vencimiento"], name="core_rangof_empresa_0a198c_idx"),
                        ],
                    },
                    managers=[
                        ("all_objects", django.db.models.manager.Manager()),
                    ],
                ),
            ],
        ),
    ]
