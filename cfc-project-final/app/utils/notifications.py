def send_notification(to_email, subject, message):
    """
    Simulation d'envoi d'email.
    Dans un système réel, utiliserait SMTP ou un service tiers.
    """
    print(f"--- [EMAIL NOTIFICATION] ---")
    print(f"TO: {to_email}")
    print(f"SUBJECT: {subject}")
    print(f"MESSAGE: {message}")
    print(f"----------------------------")
