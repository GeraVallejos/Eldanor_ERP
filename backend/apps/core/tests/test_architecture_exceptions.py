from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APPS_DIR = ROOT / "apps"


def _service_files():
    for path in APPS_DIR.rglob("services/*.py"):
        rel = path.relative_to(ROOT)
        rel_text = str(rel).replace("\\", "/")
        if "/migrations/" in rel_text or "/tests/" in rel_text or "__pycache__" in rel_text:
            continue
        yield path


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_services_do_not_import_drf_exceptions():
    offenders = []
    for path in _service_files():
        text = _read(path)
        if "from rest_framework.exceptions import" in text:
            offenders.append(str(path.relative_to(ROOT)))

    assert not offenders, (
        "Service layer must not import DRF exceptions. Offenders: " + ", ".join(offenders)
    )


def test_services_do_not_import_django_validation_error():
    offenders = []
    for path in _service_files():
        text = _read(path)
        if "from django.core.exceptions import ValidationError" in text:
            offenders.append(str(path.relative_to(ROOT)))

    assert not offenders, (
        "Service layer must not import django ValidationError. Offenders: " + ", ".join(offenders)
    )


def test_services_do_not_raise_value_error_for_business_rules():
    offenders = []
    for path in _service_files():
        text = _read(path)
        if "raise ValueError(" in text:
            offenders.append(str(path.relative_to(ROOT)))

    assert not offenders, (
        "Service layer should use AppError subclasses, not ValueError. Offenders: "
        + ", ".join(offenders)
    )


def test_global_exception_handler_is_configured():
    settings_path = ROOT / "Eldanor_ERP" / "settings.py"
    text = _read(settings_path)
    expected = '"EXCEPTION_HANDLER": "apps.core.api.exception_handler.custom_exception_handler"'
    assert expected in text
