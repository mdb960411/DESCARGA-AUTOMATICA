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
    return "OK"
