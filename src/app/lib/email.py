"""Email utility functions for sending verification emails."""

from __future__ import annotations

import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any
from uuid import UUID

import structlog

from app.config.base import SMTPSettings

logger = structlog.get_logger()


def generate_verification_token() -> str:
    """Generate a secure random verification token.

    Returns:
        A 32-character URL-safe token.
    """
    return secrets.token_urlsafe(32)


def create_verification_email_content(
    user_email: str,
    user_name: str | None,
    verification_token: str,
    base_url: str = "http://localhost:3000",
) -> tuple[str, str]:
    """Create HTML and text content for verification email.

    Args:
        user_email: The user's email address
        user_name: The user's name (optional)
        verification_token: The verification token to include in the link
        base_url: Base URL for the verification link

    Returns:
        Tuple of (html_content, text_content)
    """
    display_name = user_name or user_email
    verification_url = f"{base_url}/api/access/verify-email?token={verification_token}"

    # HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Verify your email address</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4f46e5; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 30px 20px; }}
            .button {{ 
                display: inline-block; 
                background-color: #4f46e5; 
                color: white;
                padding: 12px 30px; 
                text-decoration: none; 
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{ color: #666; font-size: 12px; text-align: center; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to Todo AI!</h1>
            </div>
            <div class="content">
                <h2>Hi {display_name},</h2>
                <p>Thanks for signing up! To complete your registration, please verify your email address by clicking the button below:</p>
                
                <div style="text-align: center;">
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                </div>
                
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #4f46e5;">{verification_url}</p>
                
                <p>This verification link will expire in 24 hours for security reasons.</p>
                
                <p>If you didn't create an account with us, please ignore this email.</p>
                
                <p>Best regards,<br>The Todo AI Team</p>
            </div>
            <div class="footer">
                <p>This is an automated message, please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Text content (fallback)
    text_content = f"""
    Welcome to Todo AI!
    
    Hi {display_name},
    
    Thanks for signing up! To complete your registration, please verify your email address by visiting this link:
    
    {verification_url}
    
    This verification link will expire in 24 hours for security reasons.
    
    If you didn't create an account with us, please ignore this email.
    
    Best regards,
    The Todo AI Team
    
    ---
    This is an automated message, please do not reply to this email.
    """

    return html_content, text_content


async def send_verification_email(
    smtp_settings: SMTPSettings,
    to_email: str,
    user_name: str | None,
    verification_token: str,
    from_email: str | None = None,
    base_url: str = "http://localhost:3000",
) -> bool:
    """Send a verification email to the user.

    Args:
        smtp_settings: SMTP configuration settings
        to_email: Recipient email address
        user_name: User's name (optional)
        verification_token: Verification token to include
        from_email: Sender email (defaults to SMTP username)
        base_url: Base URL for verification link

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        # Use SMTP username as from_email if not provided
        sender_email = from_email or smtp_settings.USERNAME
        if not sender_email:
            await logger.aerror("No sender email configured")
            return False

        # Create email content
        html_content, text_content = create_verification_email_content(
            to_email, user_name, verification_token, base_url
        )

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Verify your email address - Todo AI"
        msg["From"] = sender_email
        msg["To"] = to_email

        # Attach both text and HTML parts
        text_part = MIMEText(text_content, "plain")
        html_part = MIMEText(html_content, "html")

        msg.attach(text_part)
        msg.attach(html_part)

        # Send email
        server = None
        try:
            # Create SMTP connection
            if smtp_settings.USE_SSL and smtp_settings.PORT == 465:
                server = smtplib.SMTP_SSL(
                    smtp_settings.HOST, smtp_settings.PORT)
            else:
                server = smtplib.SMTP(smtp_settings.HOST, smtp_settings.PORT)
                if smtp_settings.USE_TLS:
                    server.starttls()

            # Authenticate if credentials are provided
            if smtp_settings.USERNAME and smtp_settings.PASSWORD:
                server.login(smtp_settings.USERNAME, smtp_settings.PASSWORD)

            # Send email
            server.send_message(msg)

            await logger.ainfo(
                "Verification email sent successfully",
                to_email=to_email,
                user_name=user_name,
            )
            return True

        finally:
            if server:
                server.quit()

    except Exception as e:
        await logger.aerror(
            "Failed to send verification email",
            error=str(e),
            to_email=to_email,
            user_name=user_name,
        )
        return False


def create_verification_storage_data(user_id: UUID, verification_token: str) -> dict[str, Any]:
    """Create data structure for storing verification token.

    This is a helper function that can be used to store verification tokens
    in a database or cache system.

    Args:
        user_id: The user's ID
        verification_token: The verification token

    Returns:
        Dictionary with verification data
    """
    from datetime import UTC, datetime, timedelta

    return {
        "user_id": str(user_id),
        "verification_token": verification_token,
        "created_at": datetime.now(UTC),
        "expires_at": datetime.now(UTC) + timedelta(hours=24),
        "is_used": False,
    }


async def send_welcome_email(
    smtp_settings: SMTPSettings,
    to_email: str,
    user_name: str | None,
    from_email: str | None = None,
) -> bool:
    """Send a welcome email after successful verification.

    Args:
        smtp_settings: SMTP configuration settings
        to_email: Recipient email address  
        user_name: User's name (optional)
        from_email: Sender email (defaults to SMTP username)

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        sender_email = from_email or smtp_settings.USERNAME
        if not sender_email:
            await logger.aerror("No sender email configured")
            return False

        display_name = user_name or to_email

        # HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Welcome to Todo AI!</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #10b981; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px 20px; }}
                .feature {{ margin: 20px 0; padding: 15px; background-color: #f9f9f9; border-radius: 5px; }}
                .footer {{ color: #666; font-size: 12px; text-align: center; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to Todo AI!</h1>
                </div>
                <div class="content">
                    <h2>Hi {display_name},</h2>
                    <p>Your email has been successfully verified! Welcome to Todo AI, your intelligent task management companion.</p>
                    
                    <div class="feature">
                        <h3>🤖 AI-Powered Task Management</h3>
                        <p>Get intelligent suggestions and automated scheduling for your tasks.</p>
                    </div>
                    
                    <div class="feature">
                        <h3>📅 Smart Scheduling</h3>
                        <p>Avoid conflicts and optimize your productivity with AI-driven scheduling.</p>
                    </div>
                    
                    <div class="feature">
                        <h3>🏷️ Intelligent Categorization</h3>
                        <p>Let AI help organize your tasks with smart tags and priorities.</p>
                    </div>
                    
                    <p>Ready to get started? Log in to your account and begin organizing your tasks with AI assistance!</p>
                    
                    <p>If you have any questions, feel free to reach out to our support team.</p>
                    
                    <p>Happy organizing!<br>The Todo AI Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message, please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Text content
        text_content = f"""
        Welcome to Todo AI!
        
        Hi {display_name},
        
        Your email has been successfully verified! Welcome to Todo AI, your intelligent task management companion.
        
        Features you can now enjoy:
        
        🤖 AI-Powered Task Management
        Get intelligent suggestions and automated scheduling for your tasks.
        
        📅 Smart Scheduling  
        Avoid conflicts and optimize your productivity with AI-driven scheduling.
        
        🏷️ Intelligent Categorization
        Let AI help organize your tasks with smart tags and priorities.
        
        Ready to get started? Log in to your account and begin organizing your tasks with AI assistance!
        
        If you have any questions, feel free to reach out to our support team.
        
        Happy organizing!
        The Todo AI Team
        
        ---
        This is an automated message, please do not reply to this email.
        """

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Welcome to Todo AI! 🎉"
        msg["From"] = sender_email
        msg["To"] = to_email

        # Attach both text and HTML parts
        text_part = MIMEText(text_content, "plain")
        html_part = MIMEText(html_content, "html")

        msg.attach(text_part)
        msg.attach(html_part)

        # Send email
        server = None
        try:
            # Create SMTP connection
            if smtp_settings.USE_SSL and smtp_settings.PORT == 465:
                server = smtplib.SMTP_SSL(
                    smtp_settings.HOST, smtp_settings.PORT)
            else:
                server = smtplib.SMTP(smtp_settings.HOST, smtp_settings.PORT)
                if smtp_settings.USE_TLS:
                    server.starttls()

            # Authenticate if credentials are provided
            if smtp_settings.USERNAME and smtp_settings.PASSWORD:
                server.login(smtp_settings.USERNAME, smtp_settings.PASSWORD)

            # Send email
            server.send_message(msg)

            await logger.ainfo(
                "Welcome email sent successfully",
                to_email=to_email,
                user_name=user_name,
            )
            return True

        finally:
            if server:
                server.quit()

    except Exception as e:
        await logger.aerror(
            "Failed to send welcome email",
            error=str(e),
            to_email=to_email,
            user_name=user_name,
        )
        return False
