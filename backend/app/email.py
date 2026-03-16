"""
Home Cloud Drive - Email utilities
"""
import smtplib
from email.message import EmailMessage

from app.config import get_settings

settings = get_settings()


def send_password_reset_email(recipient_email: str, username: str, reset_url: str) -> None:
    """Send a password reset email with a one-time reset link."""
    if not settings.password_reset_enabled:
        raise RuntimeError("Password reset email is not configured")

    message = EmailMessage()
    message["Subject"] = "Reset your Home Cloud password"
    message["From"] = (
        f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        if settings.smtp_from_name
        else settings.smtp_from_email
    )
    message["To"] = recipient_email

    text_body = (
        f"Hello {username},\n\n"
        "We received a request to reset your Home Cloud password.\n"
        f"Use this link to choose a new password:\n\n{reset_url}\n\n"
        f"This link expires in {settings.password_reset_expire_minutes} minutes.\n"
        "If you did not request this, you can safely ignore this email.\n"
    )
    html_body = (
        f"<p>Hello {username},</p>"
        "<p>We received a request to reset your Home Cloud password.</p>"
        f"<p><a href=\"{reset_url}\">Choose a new password</a></p>"
        f"<p>This link expires in {settings.password_reset_expire_minutes} minutes.</p>"
        "<p>If you did not request this, you can safely ignore this email.</p>"
    )

    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    if settings.smtp_use_ssl:
        smtp = smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        )
    else:
        smtp = smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        )

    with smtp as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
