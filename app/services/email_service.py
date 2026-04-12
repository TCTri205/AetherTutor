"""
Email Service — SMTP-based email sending with templates.

Features:
- SMTP email sending (verification, password reset)
- HTML email templates
- JWT token generation for verification (24h) and password reset (1h)
- Mock mode for development (logs instead of sending)
- Configuration from app/settings
"""
from __future__ import annotations

import smtplib
import ssl
import secrets
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import jwt
from loguru import logger

from app.config import settings


# ---------------------------------------------------------------------------
# Token constants
# ---------------------------------------------------------------------------
TOKEN_ALGORITHM = "HS256"
VERIFICATION_TOKEN_EXPIRE_HOURS = 24
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 1
VERIFICATION_TOKEN_TYPE = "email_verification"
PASSWORD_RESET_TOKEN_TYPE = "password_reset"


# ---------------------------------------------------------------------------
# HTML Email Templates
# ---------------------------------------------------------------------------

def _base_template(body_html: str, title: str) -> str:
    """Wrap content in branded HTML email template."""
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f4f7fa;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            padding: 32px 24px;
            text-align: center;
        }}
        .header h1 {{
            color: #ffffff;
            margin: 0;
            font-size: 24px;
        }}
        .content {{
            padding: 32px 24px;
            color: #334155;
            line-height: 1.6;
        }}
        .content p {{
            margin: 0 0 16px 0;
        }}
        .btn {{
            display: inline-block;
            padding: 14px 32px;
            background: #6366f1;
            color: #ffffff !important;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            margin: 16px 0;
        }}
        .footer {{
            background: #f8fafc;
            padding: 16px 24px;
            text-align: center;
            font-size: 12px;
            color: #94a3b8;
        }}
        .code {{
            background: #f1f5f9;
            padding: 12px 16px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            letter-spacing: 2px;
            word-break: break-all;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{settings.PROJECT_NAME}</h1>
        </div>
        <div class="content">
            {body_html}
        </div>
        <div class="footer">
            <p>&copy; {datetime.now(timezone.utc).year} {settings.PROJECT_NAME}. All rights reserved.</p>
            <p>This is an automated message. Please do not reply.</p>
        </div>
    </div>
</body>
</html>"""


def verification_email_template(token: str) -> str:
    """HTML template for email verification."""
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    body = f"""\
<h2>Verify Your Email Address</h2>
<p>Thank you for joining <strong>{settings.PROJECT_NAME}</strong>! To complete your registration, please verify your email address by clicking the button below:</p>
<p style="text-align: center;">
    <a href="{verify_url}" class="btn">Verify Email Address</a>
</p>
<p>Or copy and paste this link into your browser:</p>
<p class="code">{verify_url}</p>
<p><strong>This link will expire in {VERIFICATION_TOKEN_EXPIRE_HOURS} hours.</strong></p>
<p>If you did not create an account, please ignore this email.</p>"""
    return _base_template(body, "Verify Your Email")


def password_reset_email_template(token: str) -> str:
    """HTML template for password reset."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    body = f"""\
<h2>Reset Your Password</h2>
<p>We received a request to reset your password. Click the button below to create a new password:</p>
<p style="text-align: center;">
    <a href="{reset_url}" class="btn">Reset Password</a>
</p>
<p>Or copy and paste this link into your browser:</p>
<p class="code">{reset_url}</p>
<p><strong>This link will expire in {PASSWORD_RESET_TOKEN_EXPIRE_HOURS} hour(s).</strong></p>
<p>If you did not request a password reset, please ignore this email. Your account remains secure.</p>"""
    return _base_template(body, "Reset Your Password")


# ---------------------------------------------------------------------------
# Token Generation & Validation
# ---------------------------------------------------------------------------

def _get_email_jwt_secret() -> str:
    """Use a separate secret for email tokens if configured, fallback to JWT secret."""
    # For added security, could use a separate EMAIL_JWT_SECRET
    return settings.JWT_SECRET_KEY


def generate_verification_token(user_id: str, email: str) -> str:
    """
    Generate JWT token for email verification.
    
    Token expires in 24 hours and contains user_id and email for validation.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "type": VERIFICATION_TOKEN_TYPE,
        "jti": secrets.token_hex(16),  # Unique token ID for single-use
    }
    token = jwt.encode(payload, _get_email_jwt_secret(), algorithm=TOKEN_ALGORITHM)
    logger.debug(f"Generated verification token for user {user_id}")
    return token


def generate_password_reset_token(user_id: str, email: str) -> str:
    """
    Generate JWT token for password reset.
    
    Token expires in 1 hour and contains user_id and email for validation.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "type": PASSWORD_RESET_TOKEN_TYPE,
        "jti": secrets.token_hex(16),  # Unique token ID for single-use
    }
    token = jwt.encode(payload, _get_email_jwt_secret(), algorithm=TOKEN_ALGORITHM)
    logger.debug(f"Generated password reset token for user {user_id}")
    return token


def decode_email_token(token: str, expected_type: str) -> dict:
    """
    Decode and validate an email token.
    
    Args:
        token: JWT token string
        expected_type: Either 'email_verification' or 'password_reset'
        
    Returns:
        Decoded payload dict with 'sub' (user_id) and 'email'
        
    Raises:
        ValueError: If token is invalid, expired, or wrong type
    """
    try:
        payload = jwt.decode(
            token,
            _get_email_jwt_secret(),
            algorithms=[TOKEN_ALGORITHM],
            options={"require": ["exp", "sub", "email", "type"]},
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired. Please request a new one.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token. Please request a new one.")

    if payload.get("type") != expected_type:
        raise ValueError("Invalid token type.")

    return payload


# ---------------------------------------------------------------------------
# Email Sending
# ---------------------------------------------------------------------------

def _build_email_message(to_email: str, subject: str, html_body: str) -> MIMEMultipart:
    """Build a MIME email message."""
    from_email = settings.SMTP_FROM_EMAIL or "noreply@aethertutor.com"
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))
    return msg


def _send_smtp(to_email: str, subject: str, html_body: str) -> bool:
    """
    Send email via SMTP.
    
    Returns:
        True if sent successfully, False otherwise.
        
    Raises:
        smtplib.SMTPException on SMTP errors
    """
    if not settings.SMTP_HOST:
        raise RuntimeError("SMTP_HOST is not configured")
    
    msg = _build_email_message(to_email, subject, html_body)
    
    context = ssl.create_default_context()
    
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        
        from_email = settings.SMTP_FROM_EMAIL or "noreply@aethertutor.com"
        server.sendmail(from_email, to_email, msg.as_string())
    
    logger.info(f"Email sent via SMTP: to={to_email}, subject={subject}")
    return True


def _send_mock(to_email: str, subject: str, html_body: str) -> bool:
    """
    Mock email sending — log the email details instead of sending.
    Used in development/testing.
    """
    logger.info(
        "=" * 60
        + f"\n[MOCK EMAIL] To: {to_email}\n[MOCK EMAIL] Subject: {subject}\n"
        + "[MOCK EMAIL] Body preview: " + html_body[:200] + "...\n"
        + "=" * 60
    )
    return True


async def send_verification_email(to_email: str, token: str) -> bool:
    """
    Send email verification email.
    
    Args:
        to_email: Recipient email address
        token: Verification JWT token
        
    Returns:
        True if sent successfully
    """
    html_body = verification_email_template(token)
    subject = f"Verify your {settings.PROJECT_NAME} account"
    return await _send_email(to_email, subject, html_body)


async def send_password_reset_email(to_email: str, token: str) -> bool:
    """
    Send password reset email.
    
    Args:
        to_email: Recipient email address
        token: Password reset JWT token
        
    Returns:
        True if sent successfully
    """
    html_body = password_reset_email_template(token)
    subject = f"Reset your {settings.PROJECT_NAME} password"
    return await _send_email(to_email, subject, html_body)


async def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Internal email dispatcher — routes to SMTP or mock based on config.
    """
    try:
        if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
            return _send_smtp(to_email, subject, html_body)
        else:
            logger.warning(
                f"SMTP not fully configured (missing host/user/password). "
                f"Using mock mode for {to_email}"
            )
            return _send_mock(to_email, subject, html_body)
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending email to {to_email}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error sending email to {to_email}: {e}")
        raise
