from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0020_move_tesoreria_models_to_tesoreria_app"),
        ("facturacion", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="RangoFolioTributario"),
                migrations.DeleteModel(name="ConfiguracionTributaria"),
            ],
        ),
    ]
