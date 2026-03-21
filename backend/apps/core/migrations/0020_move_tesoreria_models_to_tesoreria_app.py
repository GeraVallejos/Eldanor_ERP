from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0019_alter_movimientobancario_estado_contable"),
        ("tesoreria", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="MovimientoBancario"),
                migrations.DeleteModel(name="CuentaBancariaEmpresa"),
                migrations.DeleteModel(name="TipoCambio"),
                migrations.DeleteModel(name="CuentaPorPagar"),
                migrations.DeleteModel(name="CuentaPorCobrar"),
                migrations.DeleteModel(name="Moneda"),
            ],
        ),
    ]
