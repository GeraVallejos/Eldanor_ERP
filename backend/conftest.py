import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.core.models import Empresa
from apps.core.tenant import set_current_empresa, set_current_user
from apps.core.validators import calcular_dv_rut
from apps.productos.models import Categoria


@pytest.fixture(autouse=True)
def limpiar_tenant_contexto():
    set_current_empresa(None)
    set_current_user(None)
    yield
    set_current_empresa(None)
    set_current_user(None)


def _build_test_rut(prefix: str) -> str:
    base = f"{prefix}{uuid.uuid4().int % 1000000:06d}"
    cuerpo = str(int(base))
    return f"{int(cuerpo):,}".replace(",", ".") + f"-{calcular_dv_rut(cuerpo)}"


@pytest.fixture
def empresa(db):
    uid = uuid.uuid4().hex[:8]
    return Empresa.objects.create(
        nombre=f"EMPRESA TEST {uid}",
        rut=_build_test_rut("76"),
        email=f"empresa_{uid}@test.com",
    )


@pytest.fixture
def empresa_a(db):
    uid = uuid.uuid4().hex[:8]
    return Empresa.objects.create(
        nombre=f"EMPRESA A {uid}",
        rut=_build_test_rut("77"),
        email=f"empresa_a_{uid}@test.com",
    )


@pytest.fixture
def empresa_b(db):
    uid = uuid.uuid4().hex[:8]
    return Empresa.objects.create(
        nombre=f"EMPRESA B {uid}",
        rut=_build_test_rut("78"),
        email=f"empresa_b_{uid}@test.com",
    )


@pytest.fixture
def usuario(db, empresa):
    User = get_user_model()
    uid = uuid.uuid4().hex[:8]
    return User.objects.create_user(
        username=f"usuario_{uid}",
        email=f"usuario_{uid}@test.com",
        password="pass1234",
        empresa_activa=empresa,
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def categoria(db, empresa):
    set_current_empresa(empresa)
    return Categoria.objects.create(nombre="GENERAL")
