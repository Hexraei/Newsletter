"""Email service for sending transactional emails via SendGrid."""

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_reset_email(to_email: str, reset_token: str, base_url: str) -> bool:
    """Send a password reset email. Falls back to console logging if SendGrid is not configured."""
    reset_link = f"{base_url}/auth.html?reset_token={reset_token}"

    if not settings.SENDGRID_API_KEY:
        logger.warning(
            "SENDGRID_API_KEY not set — logging reset link to console.\n"
            "  To: %s\n  Reset link: %s",
            to_email,
            reset_link,
        )
        return True

    html_content = (
        "<h2>Password Reset Request</h2>"
        "<p>You requested a password reset for your News Day account.</p>"
        f'<p><a href="{reset_link}" style="padding:10px 20px;background:#6366f1;'
        'color:#fff;border-radius:8px;text-decoration:none;">Reset Password</a></p>'
        "<p>This link expires in 1 hour. If you did not request this, ignore this email.</p>"
    )

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": settings.FROM_EMAIL},
        "subject": "News Day — Password Reset",
        "content": [{"type": "text/html", "value": html_content}],
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
        if resp.status_code in (200, 201, 202):
            logger.info("Reset email sent to %s", to_email)
            return True
        logger.error("SendGrid error %s: %s", resp.status_code, resp.text)
        return False
    except Exception:
        logger.exception("Failed to send reset email to %s", to_email)
        return False
