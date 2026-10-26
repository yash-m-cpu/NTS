"""Security and privacy utilities for WBPIS.

Enforces zero-credential leakage in logs (SEC-01 remediation),
salted ephemeral track pseudonymization, and token security.
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

# Regex pattern to match RTSP credentials in URLs
# Matches rtsp://username:password@host...
RTSP_CREDENTIAL_PATTERN = re.compile(r'(rtsp://)([^:]+):([^@]+)@', re.IGNORECASE)


def sanitize_rtsp_url(url: str) -> str:
    """Masks username and password in RTSP connection strings.

    Remediates SEC-01 by replacing plaintext passwords with asterisks.

    Example:
        >>> sanitize_rtsp_url("rtsp://admin:SecretPass123@192.168.1.50:554/live")
        'rtsp://admin:*****@192.168.1.50:554/live'
    """
    if not url:
        return ""
    return RTSP_CREDENTIAL_PATTERN.sub(r'\1\2:*****@', url)


def get_daily_salt(custom_key: Optional[str] = None) -> str:
    """Generates a daily rotating cryptographic salt string.

    Rotates every 24 hours at UTC midnight to ensure track handles
    cannot be correlated across different days.
    """
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    seed = f"{date_str}:{custom_key or 'WBPIS-EPHEMERAL-SALT'}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def generate_ephemeral_track_hash(track_id: int, camera_id: str, salt: Optional[str] = None) -> str:
    """Creates a pseudonymous session hash for an active track handle.

    Guarantees no biometric or permanent identifier is persisted.

    Args:
        track_id: Local integer track ID emitted by ByteTrack.
        camera_id: Camera identifier string.
        salt: Optional daily salt. Defaults to current daily salt.

    Returns:
        A short pseudonymous string, e.g., 'TRK-7f8a9e'.
    """
    active_salt = salt or get_daily_salt()
    raw = f"{track_id}:{camera_id}:{active_salt}"
    hash_digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    return f"TRK-{hash_digest}"
