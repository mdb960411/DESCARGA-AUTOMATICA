def is_provider_sender_confirmation(sender, subject):
    sender = str(sender or "").casefold()
    if not sender.endswith("@transfernow.net"):
        return False

    subject = str(subject or "").casefold()
    return any(
        marker in subject
        for marker in (
            "sus archivos se han enviado con éxito",
            "sus archivos se enviaron con éxito",
            "your files have been successfully sent",
            "your files were successfully sent",
            "vos fichiers ont été envoyés",
        )
    )
