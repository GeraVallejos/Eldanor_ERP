from apps.core.exceptions import BusinessRuleError


class DocumentStateService:

    allowed_transitions = {
        "BORRADOR": ["CONFIRMADO", "CANCELADO"],
        "CONFIRMADO": ["CANCELADO"],
        "CANCELADO": [],
    }

    @classmethod
    def change_state(cls, document, new_state):

        current = document.estado

        if new_state not in cls.allowed_transitions.get(current, []):
            raise BusinessRuleError(
                f"No se puede cambiar de {current} a {new_state}"
            )

        document.estado = new_state
        document.save(update_fields=["estado"])
        return document