from apps.core.exceptions import BusinessRuleError


class WorkflowService:
    """Motor reutilizable de transiciones de estado para agregados de negocio."""

    @staticmethod
    def normalize_state(value):
        """Normaliza un estado a formato canonico en mayusculas."""
        return str(value or "").strip().upper()

    @staticmethod
    def allowed_next(current_state, transitions):
        """Devuelve el conjunto de estados permitidos desde el estado actual."""
        current = WorkflowService.normalize_state(current_state)
        return set(transitions.get(current, set()))

    @staticmethod
    def assert_transition(*, current_state, next_state, transitions, error_prefix="Transicion invalida"):
        """Valida una transicion y retorna el estado destino normalizado."""
        current = WorkflowService.normalize_state(current_state)
        target = WorkflowService.normalize_state(next_state)

        if not target:
            raise BusinessRuleError("El estado destino es obligatorio.")

        allowed = WorkflowService.allowed_next(current, transitions)
        if target not in allowed:
            raise BusinessRuleError(f"{error_prefix}: {current} -> {target}.")

        return target

    @staticmethod
    def apply_transition(*, entity, state_field, next_state, transitions, persist=True, update_fields=None):
        """Aplica una transicion valida y persiste el cambio cuando corresponde."""
        current_state = getattr(entity, state_field)
        target = WorkflowService.assert_transition(
            current_state=current_state,
            next_state=next_state,
            transitions=transitions,
        )

        setattr(entity, state_field, target)
        if persist:
            fields = update_fields or [state_field]
            entity.save(update_fields=fields)

        return entity
