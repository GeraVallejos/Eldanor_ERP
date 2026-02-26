from contextvars import ContextVar

_current_empresa = ContextVar("current_empresa", default=None)
_current_user = ContextVar("current_user", default=None)


def set_current_empresa(empresa):
    _current_empresa.set(empresa)

def get_current_empresa():
    return _current_empresa.get()

def set_current_user(user): 
    return _current_user.set(user)

def get_current_user(): 
    return _current_user.get()