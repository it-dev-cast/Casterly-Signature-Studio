"""Outgoing email over SMTP (configured with SMTP_* settings)."""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger("signature_studio.email")


def is_configured() -> bool:
    return get_settings().smtp_enabled


def send_email(to: str, subject: str, html: str, text: str) -> None:
    settings = get_settings()
    if not settings.smtp_enabled:
        raise AppError(409, "EMAIL_NOT_CONFIGURED", "Automatic email sending isn't set up yet (SMTP settings are missing).")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_username
    msg["To"] = to
    msg["Message-ID"] = make_msgid(domain=(settings.smtp_from or settings.smtp_username).split("@")[-1].strip(">") or None)
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    try:
        if settings.smtp_security == "ssl":
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
        with server:
            if settings.smtp_security == "starttls":
                server.starttls(context=ssl.create_default_context())
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        logger.warning("SMTP login failed for %s", settings.smtp_username)
        raise AppError(502, "EMAIL_LOGIN_FAILED", "The email server rejected the SMTP username or password.") from None
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("SMTP send failed: %s", exc)
        raise AppError(502, "EMAIL_SEND_FAILED", "The email could not be sent. Check the SMTP settings and try again.") from None
