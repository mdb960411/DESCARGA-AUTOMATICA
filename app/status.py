def manual_action_for_reason(reason, enabled):
    if enabled and reason and "Cloudflare" in reason:
        return (
            "Requiere descarga manual porque Cloudflare no completó "
            "la validación en Cloud Run"
        )
    return None


def execution_status(summary):
    if summary["messages_failed"] or summary["messages_partial"]:
        return "COMPLETADO_CON_ERRORES"
    if summary["messages_manual"]:
        return "REQUIERE_ATENCION_MANUAL"
    if summary.get("messages_retry_pending", 0):
        return "REINTENTOS_PENDIENTES"
    return "OK"


def next_retry_attempt(previous_attempt, retryable, max_runs):
    if not retryable:
        return None

    next_attempt = max(0, previous_attempt) + 1
    if next_attempt >= max_runs:
        return None
    return next_attempt
