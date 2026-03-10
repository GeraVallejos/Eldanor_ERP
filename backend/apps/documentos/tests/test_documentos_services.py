from decimal import Decimal

import pytest

from apps.core.exceptions import BusinessRuleError
from apps.documentos.services.estado_service import DocumentStateService
from apps.documentos.services.total_service import DocumentTotalsService


@pytest.mark.django_db
class TestDocumentStateService:
    def test_change_state_valido_actualiza_documento(self):
        class DocumentoDummy:
            estado = "BORRADOR"

            def save(self, *args, **kwargs):
                return None

        doc = DocumentoDummy()
        actualizado = DocumentStateService.change_state(doc, "CONFIRMADO")

        assert actualizado.estado == "CONFIRMADO"

    def test_change_state_invalido_lanza_business_rule(self):
        class DocumentoDummy:
            estado = "CONFIRMADO"

            def save(self, *args, **kwargs):
                return None

        with pytest.raises(BusinessRuleError):
            DocumentStateService.change_state(DocumentoDummy(), "BORRADOR")


@pytest.mark.django_db
class TestDocumentTotalsService:
    def test_calcular_totales_asigna_subtotal_impuestos_y_total(self):
        class DummyItems:
            def __init__(self, items):
                self._items = items

            def all(self):
                return self._items

        class DummyItem:
            def __init__(self, subtotal, total):
                self.subtotal = subtotal
                self.total = total

        class DummyDocumento:
            def __init__(self):
                self.subtotal = Decimal("0")
                self.impuesto_total = Decimal("0")
                self.total = Decimal("0")
                self.items = DummyItems(
                    [
                        DummyItem(Decimal("200"), Decimal("238")),
                        DummyItem(Decimal("50"), Decimal("59.5")),
                    ]
                )

            def save(self, *args, **kwargs):
                return None

        documento = DummyDocumento()
        DocumentTotalsService.calcular_totales(documento)

        assert documento.subtotal == Decimal("250")
        assert documento.impuesto_total == Decimal("47.5")
        assert documento.total == Decimal("297.5")
