from django.db import migrations


TESORERIA_CLEANUP_SQL = """
ALTER TABLE `tesoreria_moneda`
  DROP FOREIGN KEY `core_moneda_creado_por_id_b49e1a2e_fk_core_user_id`,
  DROP FOREIGN KEY `core_moneda_empresa_id_aa0aab90_fk_core_empresa_id`;
ALTER TABLE `tesoreria_moneda`
  RENAME INDEX `core_moneda_creado_por_id_b49e1a2e_fk_core_user_id` TO `tes_moneda_creado_por_idx`;
ALTER TABLE `tesoreria_moneda`
  ADD CONSTRAINT `tes_moneda_creado_por_fk` FOREIGN KEY (`creado_por_id`) REFERENCES `core_user` (`id`),
  ADD CONSTRAINT `tes_moneda_empresa_fk` FOREIGN KEY (`empresa_id`) REFERENCES `core_empresa` (`id`);

ALTER TABLE `tesoreria_cuentaporcobrar`
  DROP FOREIGN KEY `core_cuentaporcobrar_cliente_id_1c1385d7_fk_contactos_cliente_id`,
  DROP FOREIGN KEY `core_cuentaporcobrar_creado_por_id_cd4c21a6_fk_core_user_id`,
  DROP FOREIGN KEY `core_cuentaporcobrar_empresa_id_2642225a_fk_core_empresa_id`,
  DROP FOREIGN KEY `core_cuentaporcobrar_moneda_id_d1fcc555_fk_core_moneda_id`;
ALTER TABLE `tesoreria_cuentaporcobrar`
  RENAME INDEX `core_cuentaporcobrar_cliente_id_1c1385d7_fk_contactos_cliente_id` TO `tes_cxc_cliente_idx`,
  RENAME INDEX `core_cuentaporcobrar_creado_por_id_cd4c21a6_fk_core_user_id` TO `tes_cxc_creado_por_idx`,
  RENAME INDEX `core_cuentaporcobrar_moneda_id_d1fcc555_fk_core_moneda_id` TO `tes_cxc_moneda_idx`;
ALTER TABLE `tesoreria_cuentaporcobrar`
  ADD CONSTRAINT `tes_cxc_cliente_fk` FOREIGN KEY (`cliente_id`) REFERENCES `contactos_cliente` (`id`),
  ADD CONSTRAINT `tes_cxc_creado_por_fk` FOREIGN KEY (`creado_por_id`) REFERENCES `core_user` (`id`),
  ADD CONSTRAINT `tes_cxc_empresa_fk` FOREIGN KEY (`empresa_id`) REFERENCES `core_empresa` (`id`),
  ADD CONSTRAINT `tes_cxc_moneda_fk` FOREIGN KEY (`moneda_id`) REFERENCES `tesoreria_moneda` (`id`);

ALTER TABLE `tesoreria_cuentaporpagar`
  DROP FOREIGN KEY `core_cuentaporpagar_creado_por_id_d9cbc838_fk_core_user_id`,
  DROP FOREIGN KEY `core_cuentaporpagar_documento_compra_id_f055355e_fk_compras_d`,
  DROP FOREIGN KEY `core_cuentaporpagar_empresa_id_333539ce_fk_core_empresa_id`,
  DROP FOREIGN KEY `core_cuentaporpagar_moneda_id_7254b5a8_fk_core_moneda_id`,
  DROP FOREIGN KEY `core_cuentaporpagar_proveedor_id_ebb601ec_fk_contactos`;
ALTER TABLE `tesoreria_cuentaporpagar`
  RENAME INDEX `core_cuentaporpagar_creado_por_id_d9cbc838_fk_core_user_id` TO `tes_cxp_creado_por_idx`,
  RENAME INDEX `core_cuentaporpagar_moneda_id_7254b5a8_fk_core_moneda_id` TO `tes_cxp_moneda_idx`,
  RENAME INDEX `core_cuentaporpagar_proveedor_id_ebb601ec_fk_contactos` TO `tes_cxp_proveedor_idx`;
ALTER TABLE `tesoreria_cuentaporpagar`
  ADD CONSTRAINT `tes_cxp_creado_por_fk` FOREIGN KEY (`creado_por_id`) REFERENCES `core_user` (`id`),
  ADD CONSTRAINT `tes_cxp_doc_compra_fk` FOREIGN KEY (`documento_compra_id`) REFERENCES `compras_documentocompraproveedor` (`id`),
  ADD CONSTRAINT `tes_cxp_empresa_fk` FOREIGN KEY (`empresa_id`) REFERENCES `core_empresa` (`id`),
  ADD CONSTRAINT `tes_cxp_moneda_fk` FOREIGN KEY (`moneda_id`) REFERENCES `tesoreria_moneda` (`id`),
  ADD CONSTRAINT `tes_cxp_proveedor_fk` FOREIGN KEY (`proveedor_id`) REFERENCES `contactos_proveedor` (`id`);

ALTER TABLE `tesoreria_tipocambio`
  DROP FOREIGN KEY `core_tipocambio_creado_por_id_ccf6766b_fk_core_user_id`,
  DROP FOREIGN KEY `core_tipocambio_empresa_id_de4d6c1f_fk_core_empresa_id`,
  DROP FOREIGN KEY `core_tipocambio_moneda_destino_id_2642a95a_fk_core_moneda_id`,
  DROP FOREIGN KEY `core_tipocambio_moneda_origen_id_3581d5fe_fk_core_moneda_id`;
ALTER TABLE `tesoreria_tipocambio`
  RENAME INDEX `core_tipocambio_creado_por_id_ccf6766b_fk_core_user_id` TO `tes_tipocambio_creado_por_idx`,
  RENAME INDEX `core_tipocambio_moneda_destino_id_2642a95a_fk_core_moneda_id` TO `tes_tipocambio_mon_dest_idx`,
  RENAME INDEX `core_tipocambio_moneda_origen_id_3581d5fe_fk_core_moneda_id` TO `tes_tipocambio_mon_ori_idx`;
ALTER TABLE `tesoreria_tipocambio`
  ADD CONSTRAINT `tes_tipocambio_creado_por_fk` FOREIGN KEY (`creado_por_id`) REFERENCES `core_user` (`id`),
  ADD CONSTRAINT `tes_tipocambio_empresa_fk` FOREIGN KEY (`empresa_id`) REFERENCES `core_empresa` (`id`),
  ADD CONSTRAINT `tes_tipocambio_mon_dest_fk` FOREIGN KEY (`moneda_destino_id`) REFERENCES `tesoreria_moneda` (`id`),
  ADD CONSTRAINT `tes_tipocambio_mon_ori_fk` FOREIGN KEY (`moneda_origen_id`) REFERENCES `tesoreria_moneda` (`id`);

ALTER TABLE `tesoreria_cuentabancariaempresa`
  DROP FOREIGN KEY `core_cuentabancariae_creado_por_id_f0f36925_fk_core_user`,
  DROP FOREIGN KEY `core_cuentabancariae_empresa_id_bc2b2bf4_fk_core_empr`,
  DROP FOREIGN KEY `core_cuentabancariaempresa_moneda_id_0b5c8d45_fk_core_moneda_id`;
ALTER TABLE `tesoreria_cuentabancariaempresa`
  RENAME INDEX `core_cuentabancariae_creado_por_id_f0f36925_fk_core_user` TO `tes_ctabco_creado_por_idx`,
  RENAME INDEX `core_cuentabancariaempresa_moneda_id_0b5c8d45_fk_core_moneda_id` TO `tes_ctabco_moneda_idx`;
ALTER TABLE `tesoreria_cuentabancariaempresa`
  ADD CONSTRAINT `tes_ctabco_creado_por_fk` FOREIGN KEY (`creado_por_id`) REFERENCES `core_user` (`id`),
  ADD CONSTRAINT `tes_ctabco_empresa_fk` FOREIGN KEY (`empresa_id`) REFERENCES `core_empresa` (`id`),
  ADD CONSTRAINT `tes_ctabco_moneda_fk` FOREIGN KEY (`moneda_id`) REFERENCES `tesoreria_moneda` (`id`);

ALTER TABLE `tesoreria_movimientobancario`
  DROP FOREIGN KEY `core_movimientobanca_cuenta_bancaria_id_ddecbf47_fk_core_cuen`,
  DROP FOREIGN KEY `core_movimientobanca_cuenta_por_cobrar_id_5bb6f6e2_fk_core_cuen`,
  DROP FOREIGN KEY `core_movimientobanca_cuenta_por_pagar_id_da4b1b70_fk_core_cuen`,
  DROP FOREIGN KEY `core_movimientobancario_creado_por_id_c4f08e9b_fk_core_user_id`,
  DROP FOREIGN KEY `core_movimientobancario_empresa_id_06ad633e_fk_core_empresa_id`;
ALTER TABLE `tesoreria_movimientobancario`
  RENAME INDEX `core_movimientobancario_creado_por_id_c4f08e9b_fk_core_user_id` TO `tes_movbco_creado_por_idx`,
  RENAME INDEX `core_movimientobanca_cuenta_bancaria_id_ddecbf47_fk_core_cuen` TO `tes_movbco_ctabco_idx`,
  RENAME INDEX `core_movimientobanca_cuenta_por_cobrar_id_5bb6f6e2_fk_core_cuen` TO `tes_movbco_cxc_idx`,
  RENAME INDEX `core_movimientobanca_cuenta_por_pagar_id_da4b1b70_fk_core_cuen` TO `tes_movbco_cxp_idx`;
ALTER TABLE `tesoreria_movimientobancario`
  ADD CONSTRAINT `tes_movbco_ctabco_fk` FOREIGN KEY (`cuenta_bancaria_id`) REFERENCES `tesoreria_cuentabancariaempresa` (`id`),
  ADD CONSTRAINT `tes_movbco_cxc_fk` FOREIGN KEY (`cuenta_por_cobrar_id`) REFERENCES `tesoreria_cuentaporcobrar` (`id`),
  ADD CONSTRAINT `tes_movbco_cxp_fk` FOREIGN KEY (`cuenta_por_pagar_id`) REFERENCES `tesoreria_cuentaporpagar` (`id`),
  ADD CONSTRAINT `tes_movbco_creado_por_fk` FOREIGN KEY (`creado_por_id`) REFERENCES `core_user` (`id`),
  ADD CONSTRAINT `tes_movbco_empresa_fk` FOREIGN KEY (`empresa_id`) REFERENCES `core_empresa` (`id`);

ALTER TABLE `compras_documentocompraproveedor`
  DROP FOREIGN KEY `compras_documentocom_moneda_id_34da21ce_fk_core_mone`;
ALTER TABLE `compras_documentocompraproveedor`
  RENAME INDEX `compras_documentocom_moneda_id_34da21ce_fk_core_mone` TO `compras_doc_moneda_idx`;
ALTER TABLE `compras_documentocompraproveedor`
  ADD CONSTRAINT `compras_doc_moneda_fk` FOREIGN KEY (`moneda_id`) REFERENCES `tesoreria_moneda` (`id`);

ALTER TABLE `productos_producto`
  DROP FOREIGN KEY `productos_producto_moneda_id_c3748a2f_fk_core_moneda_id`;
ALTER TABLE `productos_producto`
  RENAME INDEX `productos_producto_moneda_id_c3748a2f_fk_core_moneda_id` TO `prod_producto_moneda_idx`;
ALTER TABLE `productos_producto`
  ADD CONSTRAINT `prod_producto_moneda_fk` FOREIGN KEY (`moneda_id`) REFERENCES `tesoreria_moneda` (`id`);

ALTER TABLE `productos_listaprecio`
  DROP FOREIGN KEY `productos_listaprecio_moneda_id_08d4c561_fk_core_moneda_id`;
ALTER TABLE `productos_listaprecio`
  RENAME INDEX `productos_listaprecio_moneda_id_08d4c561_fk_core_moneda_id` TO `prod_lista_moneda_idx`;
ALTER TABLE `productos_listaprecio`
  ADD CONSTRAINT `prod_lista_moneda_fk` FOREIGN KEY (`moneda_id`) REFERENCES `tesoreria_moneda` (`id`);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("tesoreria", "0003_rename_core_cuenta_empresa_f7efb4_idx_tes_cta_banco_empresa_activa_idx_and_more"),
        ("compras", "0018_move_moneda_relation_to_tesoreria"),
        ("productos", "0007_move_moneda_relation_to_tesoreria"),
    ]

    operations = [
        migrations.RunSQL(TESORERIA_CLEANUP_SQL, reverse_sql=migrations.RunSQL.noop),
    ]
