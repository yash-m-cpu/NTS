import logging

logger = logging.getLogger(__name__)

async def send_verification_email(email: str, token: str):
    logger.info(f"Sending verification email to {email} with token: {token}")

async def send_password_reset_email(email: str, token: str):
    logger.info(f"Sending password reset email to {email} with token: {token}")
