"""Sanitized structured logging subsystem for WBPIS.

Ensures that no plaintext credentials or sensitive RTSP connection
strings can leak into console outputs, log files, or error traces.
"""

import logging
import os
import sys
from typing import Optional

from src.core.security import sanitize_rtsp_url


class CredentialSanitizingFilter(logging.Filter):
    """Logging filter that scrubs plaintext passwords from RTSP URLs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_rtsp_url(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: sanitize_rtsp_url(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    sanitize_rtsp_url(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True


def setup_logger(
    name: str = "wbpis",
    log_dir: str = "logs",
    log_level: int = logging.INFO,
    log_to_file: bool = True
) -> logging.Logger:
    """Configures and returns an enterprise logger with credential sanitization."""
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    # Credential sanitizing filter
    sanitizer = CredentialSanitizingFilter()

    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(sanitizer)
    logger.addHandler(console_handler)

    # File Handler
    if log_to_file:
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, "wbpis_system.log")
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sanitizer)
        logger.addHandler(file_handler)

    return logger


# Default application logger instance
logger = setup_logger()
