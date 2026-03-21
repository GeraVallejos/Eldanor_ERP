from django.db import migrations


FACTURACION_CLEANUP_SQL = """
ALTER TABLE `facturacion_configuraciontributaria`
  DROP FOREIGN KEY `core_configuraciontr_creado_por_id_0998a369_fk_core_user`,
  DROP FOREIGN KEY `core_configuraciontr_empresa_id_866e5071_fk_core_empr`;
ALTER TABLE `facturacion_configuraciontributaria`
  RENAME INDEX `core_configuraciontr_creado_por_id_0998a369_fk_core_user` TO `fac_cfg_creado_por_idx`;
ALTER TABLE `facturacion_configuraciontributaria`
  ADD CONSTRAINT `fac_cfg_creado_por_fk` FOREIGN KEY (`creado_por_id`) REFERENCES `core_user` (`id`),
  ADD CONSTRAINT `fac_cfg_empresa_fk` FOREIGN KEY (`empresa_id`) REFERENCES `core_empresa` (`id`);

ALTER TABLE `facturacion_rangofoliotributario`
  DROP FOREIGN KEY `core_rangofoliotributario_creado_por_id_b85af380_fk_core_user_id`,
  DROP FOREIGN KEY `core_rangofoliotributario_empresa_id_d5ef0947_fk_core_empresa_id`;
ALTER TABLE `facturacion_rangofoliotributario`
  RENAME INDEX `core_rangofoliotributario_creado_por_id_b85af380_fk_core_user_id` TO `fac_rango_creado_por_idx`;
ALTER TABLE `facturacion_rangofoliotributario`
  ADD CONSTRAINT `fac_rango_creado_por_fk` FOREIGN KEY (`creado_por_id`) REFERENCES `core_user` (`id`),
  ADD CONSTRAINT `fac_rango_empresa_fk` FOREIGN KEY (`empresa_id`) REFERENCES `core_empresa` (`id`);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("facturacion", "0002_rename_core_config_empresa_16c229_idx_fac_config_empresa_activa_idx_and_more"),
    ]

    operations = [
        migrations.RunSQL(FACTURACION_CLEANUP_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
