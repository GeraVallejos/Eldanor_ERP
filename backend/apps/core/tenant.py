from contextvars import ContextVar

_current_empresa = ContextVar("current_empresa", default=None)


def set_current_empresa(empresa):
    _current_empresa.set(empresa)


def get_current_empresa():
    return _current_empresa.get()