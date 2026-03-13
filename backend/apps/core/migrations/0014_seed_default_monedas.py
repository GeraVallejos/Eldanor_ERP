from decimal import Decimal

from django.db import migrations


def seed_default_currencies(apps, schema_editor):
    Empresa = apps.get_model('core', 'Empresa')
    Moneda = apps.get_model('core', 'Moneda')
    moneda_manager = Moneda._base_manager

    for empresa in Empresa.objects.all():
        clp, created = moneda_manager.get_or_create(
            empresa=empresa,
            codigo='CLP',
            defaults={
                'nombre': 'Peso Chileno',
                'simbolo': '$',
                'decimales': 2,
                'tasa_referencia': Decimal('1'),
                'es_base': True,
                'activa': True,
            },
        )
        if not created and not clp.es_base:
            clp.es_base = True
            clp.tasa_referencia = Decimal('1')
            clp.activa = True
            clp.save(update_fields=['es_base', 'tasa_referencia', 'activa'])

        moneda_manager.get_or_create(
            empresa=empresa,
            codigo='USD',
            defaults={
                'nombre': 'Dolar Estadounidense',
                'simbolo': 'US$',
                'decimales': 2,
                'tasa_referencia': Decimal('950'),
                'es_base': False,
                'activa': True,
            },
        )

        moneda_manager.filter(empresa=empresa, es_base=True).exclude(pk=clp.pk).update(es_base=False)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_moneda'),
    ]

    operations = [
        migrations.RunPython(seed_default_currencies, noop_reverse),
    ]