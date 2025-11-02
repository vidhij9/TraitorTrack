"""
Two-Factor Authentication (TOTP) utilities for TraitorTrack.
Provides TOTP secret generation, QR code creation, and verification.
"""

import pyotp
import qrcode
import io
import base64
from typing import Tuple


class TwoFactorAuth:
    """Two-Factor Authentication helper class using TOTP"""
    
    @staticmethod
    def generate_secret() -> str:
        """
        Generate a new TOTP secret key.
        
        Returns:
            Base32-encoded secret key
        """
        return pyotp.random_base32()
    
    @staticmethod
    def get_totp_uri(secret: str, username: str, issuer: str = "TraitorTrack") -> str:
        """
        Generate a TOTP provisioning URI for QR code.
        
        Args:
            secret: Base32-encoded TOTP secret
            username: User's username
            issuer: Application name (default: "TraitorTrack")
            
        Returns:
            TOTP provisioning URI
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=username,
            issuer_name=issuer
        )
    
    @staticmethod
    def generate_qr_code(uri: str) -> str:
        """
        Generate a QR code image from TOTP URI.
        
        Args:
            uri: TOTP provisioning URI
            
        Returns:
            Base64-encoded PNG image data (data URI)
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"
    
    @staticmethod
    def verify_totp(secret: str, token: str) -> bool:
        """
        Verify a TOTP token against the secret.
        
        Args:
            secret: Base32-encoded TOTP secret
            token: 6-digit TOTP code from authenticator app
            
        Returns:
            True if token is valid, False otherwise
        """
        if not secret or not token:
            return False
        
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=1)
        except Exception:
            return False
    
    @staticmethod
    def setup_2fa_for_user(user, secret: str = None) -> Tuple[str, str]:
        """
        Set up 2FA for a user by generating secret and QR code.
        
        Args:
            user: User model instance
            secret: Optional pre-generated secret (if None, generates new one)
            
        Returns:
            Tuple of (totp_secret, qr_code_data_uri)
        """
        if not secret:
            secret = TwoFactorAuth.generate_secret()
        
        uri = TwoFactorAuth.get_totp_uri(secret, user.username)
        qr_code = TwoFactorAuth.generate_qr_code(uri)
        
        return secret, qr_code
