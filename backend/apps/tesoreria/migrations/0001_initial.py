import apps.core.mixins
import django.db.models.deletion
import django.db.models.manager
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0019_alter_movimientobancario_estado_contable"),
        ("compras", "0016_documentocompraproveedor_estado_contable_and_more"),
        ("contactos", "0003_alter_direccion_tipo"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="Moneda",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("creado_en", models.DateTimeField(auto_now_add=True)),
                        ("actualizado_en", models.DateTimeField(auto_now=True)),
                        ("codigo", models.CharField(max_length=3)),
                        ("nombre", models.CharField(max_length=80)),
                        ("simbolo", models.CharField(blank=True, max_length=10)),
                        ("decimales", models.PositiveSmallIntegerField(default=2)),
                        ("tasa_referencia", models.DecimalField(decimal_places=6, default=1, max_digits=18)),
                        ("es_base", models.BooleanField(default=False)),
                        ("activa", models.BooleanField(default=True)),
                        ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_creados", to=settings.AUTH_USER_MODEL)),
                        ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_registros", to="core.empresa")),
                    ],
                    options={
                        "db_table": "core_moneda",
                        "ordering": ["codigo"],
                        "constraints": [models.UniqueConstraint(fields=("empresa", "codigo"), name="unique_moneda_codigo_por_empresa")],
                    },
                    managers=[("all_objects", django.db.models.manager.Manager())],
                ),
                migrations.AddIndex(
                    model_name="moneda",
                    index=models.Index(fields=["empresa", "codigo"], name="tesoreria_m_empresa_91b345_idx"),
                ),
                migrations.AddIndex(
                    model_name="moneda",
                    index=models.Index(fields=["empresa", "activa"], name="tesoreria_m_empresa_227661_idx"),
                ),
                migrations.CreateModel(
                    name="CuentaPorCobrar",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("creado_en", models.DateTimeField(auto_now_add=True)),
                        ("actualizado_en", models.DateTimeField(auto_now=True)),
                        ("referencia", models.CharField(max_length=100)),
                        ("fecha_emision", models.DateField()),
                        ("fecha_vencimiento", models.DateField()),
                        ("monto_total", models.DecimalField(decimal_places=2, max_digits=14)),
                        ("saldo", models.DecimalField(decimal_places=2, max_digits=14)),
                        ("estado", models.CharField(choices=[("PENDIENTE", "Pendiente"), ("PARCIAL", "Parcial"), ("PAGADA", "Pagada"), ("VENCIDA", "Vencida"), ("ANULADA", "Anulada")], default="PENDIENTE", max_length=20)),
                        ("cliente", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cuentas_por_cobrar", to="contactos.cliente")),
                        ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_creados", to=settings.AUTH_USER_MODEL)),
                        ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_registros", to="core.empresa")),
                        ("moneda", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cuentas_por_cobrar", to="tesoreria.moneda")),
                    ],
                    options={
                        "db_table": "core_cuentaporcobrar",
                        "constraints": [models.UniqueConstraint(fields=("empresa", "referencia"), name="uniq_cxc_referencia_empresa")],
                    },
                    managers=[("all_objects", django.db.models.manager.Manager())],
                ),
                migrations.AddIndex(
                    model_name="cuentaporcobrar",
                    index=models.Index(fields=["empresa", "cliente", "estado"], name="tesoreria_c_empresa_a04aea_idx"),
                ),
                migrations.AddIndex(
                    model_name="cuentaporcobrar",
                    index=models.Index(fields=["empresa", "fecha_vencimiento"], name="tesoreria_c_empresa_3800fc_idx"),
                ),
                migrations.CreateModel(
                    name="CuentaPorPagar",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("creado_en", models.DateTimeField(auto_now_add=True)),
                        ("actualizado_en", models.DateTimeField(auto_now=True)),
                        ("referencia", models.CharField(max_length=100)),
                        ("fecha_emision", models.DateField()),
                        ("fecha_vencimiento", models.DateField()),
                        ("monto_total", models.DecimalField(decimal_places=2, max_digits=14)),
                        ("saldo", models.DecimalField(decimal_places=2, max_digits=14)),
                        ("estado", models.CharField(choices=[("PENDIENTE", "Pendiente"), ("PARCIAL", "Parcial"), ("PAGADA", "Pagada"), ("VENCIDA", "Vencida"), ("ANULADA", "Anulada")], default="PENDIENTE", max_length=20)),
                        ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_creados", to=settings.AUTH_USER_MODEL)),
                        ("documento_compra", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="cuenta_por_pagar", to="compras.documentocompraproveedor")),
                        ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_registros", to="core.empresa")),
                        ("moneda", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cuentas_por_pagar", to="tesoreria.moneda")),
                        ("proveedor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cuentas_por_pagar", to="contactos.proveedor")),
                    ],
                    options={
                        "db_table": "core_cuentaporpagar",
                        "constraints": [models.UniqueConstraint(fields=("empresa", "referencia"), name="uniq_cxp_referencia_empresa")],
                    },
                    managers=[("all_objects", django.db.models.manager.Manager())],
                ),
                migrations.AddIndex(
                    model_name="cuentaporpagar",
                    index=models.Index(fields=["empresa", "proveedor", "estado"], name="tesoreria_c_empresa_3bd301_idx"),
                ),
                migrations.AddIndex(
                    model_name="cuentaporpagar",
                    index=models.Index(fields=["empresa", "fecha_vencimiento"], name="tesoreria_c_empresa_47f820_idx"),
                ),
                migrations.CreateModel(
                    name="TipoCambio",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("creado_en", models.DateTimeField(auto_now_add=True)),
                        ("actualizado_en", models.DateTimeField(auto_now=True)),
                        ("fecha", models.DateField()),
                        ("tasa", models.DecimalField(decimal_places=6, max_digits=18)),
                        ("observacion", models.CharField(blank=True, max_length=255)),
                        ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_creados", to=settings.AUTH_USER_MODEL)),
                        ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_registros", to="core.empresa")),
                        ("moneda_destino", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tipos_cambio_destino", to="tesoreria.moneda")),
                        ("moneda_origen", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tipos_cambio_origen", to="tesoreria.moneda")),
                    ],
                    options={
                        "db_table": "core_tipocambio",
                        "ordering": ["-fecha"],
                        "constraints": [models.UniqueConstraint(fields=("empresa", "moneda_origen", "moneda_destino", "fecha"), name="uniq_tipo_cambio_por_fecha")],
                    },
                    managers=[("all_objects", django.db.models.manager.Manager())],
                ),
                migrations.AddIndex(
                    model_name="tipocambio",
                    index=models.Index(fields=["empresa", "fecha"], name="tesoreria_t_empresa_a44b52_idx"),
                ),
                migrations.AddIndex(
                    model_name="tipocambio",
                    index=models.Index(fields=["empresa", "moneda_origen", "moneda_destino", "fecha"], name="tesoreria_t_empresa_1872c6_idx"),
                ),
                migrations.CreateModel(
                    name="CuentaBancariaEmpresa",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("creado_en", models.DateTimeField(auto_now_add=True)),
                        ("actualizado_en", models.DateTimeField(auto_now=True)),
                        ("alias", models.CharField(max_length=100)),
                        ("banco", models.CharField(max_length=120)),
                        ("tipo_cuenta", models.CharField(choices=[("CORRIENTE", "Cuenta corriente"), ("VISTA", "Cuenta vista"), ("AHORRO", "Cuenta de ahorro")], max_length=20)),
                        ("numero_cuenta", models.CharField(max_length=50)),
                        ("titular", models.CharField(max_length=150)),
                        ("saldo_referencial", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                        ("activa", models.BooleanField(default=True)),
                        ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_creados", to=settings.AUTH_USER_MODEL)),
                        ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_registros", to="core.empresa")),
                        ("moneda", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="cuentas_bancarias_empresa", to="tesoreria.moneda")),
                    ],
                    bases=(apps.core.mixins.TenantRelationValidationMixin, models.Model),
                    options={
                        "db_table": "core_cuentabancariaempresa",
                        "constraints": [models.UniqueConstraint(fields=("empresa", "numero_cuenta"), name="uniq_cuenta_bancaria_empresa_numero")],
                    },
                    managers=[("all_objects", django.db.models.manager.Manager())],
                ),
                migrations.AddIndex(
                    model_name="cuentabancariaempresa",
                    index=models.Index(fields=["empresa", "activa"], name="core_cuenta_empresa_f7efb4_idx"),
                ),
                migrations.AddIndex(
                    model_name="cuentabancariaempresa",
                    index=models.Index(fields=["empresa", "banco"], name="core_cuenta_empresa_0e7816_idx"),
                ),
                migrations.CreateModel(
                    name="MovimientoBancario",
                    fields=[
                        ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                        ("creado_en", models.DateTimeField(auto_now_add=True)),
                        ("actualizado_en", models.DateTimeField(auto_now=True)),
                        ("fecha", models.DateField()),
                        ("referencia", models.CharField(blank=True, max_length=120)),
                        ("descripcion", models.CharField(blank=True, max_length=255)),
                        ("tipo", models.CharField(choices=[("CREDITO", "Credito"), ("DEBITO", "Debito")], max_length=20)),
                        ("monto", models.DecimalField(decimal_places=2, max_digits=14)),
                        ("origen", models.CharField(choices=[("MANUAL", "Manual"), ("IMPORTACION", "Importacion"), ("CONCILIACION", "Conciliacion")], default="MANUAL", max_length=20)),
                        ("estado_contable", models.CharField(choices=[("NO_APLICA", "No aplica"), ("PENDIENTE", "Pendiente"), ("CONTABILIZADO", "Contabilizado"), ("ERROR", "Error")], default="NO_APLICA", max_length=20)),
                        ("conciliado", models.BooleanField(default=False)),
                        ("conciliado_en", models.DateTimeField(blank=True, null=True)),
                        ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_creados", to=settings.AUTH_USER_MODEL)),
                        ("cuenta_bancaria", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="movimientos_bancarios", to="tesoreria.cuentabancariaempresa")),
                        ("cuenta_por_cobrar", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movimientos_bancarios", to="tesoreria.cuentaporcobrar")),
                        ("cuenta_por_pagar", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movimientos_bancarios", to="tesoreria.cuentaporpagar")),
                        ("empresa", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="%(class)s_registros", to="core.empresa")),
                    ],
                    bases=(apps.core.mixins.TenantRelationValidationMixin, models.Model),
                    options={"db_table": "core_movimientobancario"},
                    managers=[("all_objects", django.db.models.manager.Manager())],
                ),
                migrations.AddIndex(
                    model_name="movimientobancario",
                    index=models.Index(fields=["empresa", "fecha"], name="core_movimi_empresa_16a7d1_idx"),
                ),
                migrations.AddIndex(
                    model_name="movimientobancario",
                    index=models.Index(fields=["empresa", "conciliado"], name="core_movimi_empresa_1ecac4_idx"),
                ),
                migrations.AddIndex(
                    model_name="movimientobancario",
                    index=models.Index(fields=["empresa", "cuenta_bancaria", "fecha"], name="core_movimi_empresa_69a4ae_idx"),
                ),
            ],
        ),
    ]
