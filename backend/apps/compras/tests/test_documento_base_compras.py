from apps.compras.models import OrdenCompra, OrdenCompraItem
from apps.documentos.models import DocumentoItemBase, DocumentoTributableBase


def test_orden_compra_hereda_documento_tributable_base():
    assert issubclass(OrdenCompra, DocumentoTributableBase)


def test_orden_compra_item_hereda_documento_item_base():
    assert issubclass(OrdenCompraItem, DocumentoItemBase)
