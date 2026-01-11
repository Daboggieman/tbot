import logging
import os
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """Base exception for security-related errors."""
    pass

class DecryptionError(SecurityError):
    """Raised when a message cannot be decrypted."""
    pass

class ConfigurationError(SecurityError):
    """Raised when security configuration is missing or invalid."""
    pass

def generate_key():
    """Generates a key for Fernet encryption."""
    key = Fernet.generate_key()
    logger.info("Generated a new Fernet key. Store this securely!")
    return key.decode()

def encrypt_message(message, key):
    """Encrypts a message using the provided key."""
    try:
        f = Fernet(key)
        return f.encrypt(message.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise SecurityError(f"Failed to encrypt message: {e}")

def decrypt_message(encrypted_message, key):
    """Decrypts a message using the provided key."""
    try:
        f = Fernet(key)
        if isinstance(encrypted_message, str):
            encrypted_message = encrypted_message.encode()
        return f.decrypt(encrypted_message).decode()
    except Exception as e:
        logger.error(f"Decryption failed. Ensure the ENCRYPTION_KEY is correct. Error: {e}")
        raise DecryptionError(f"Could not decrypt message. This usually means the ENCRYPTION_KEY is wrong or the data is malformed.")

def get_encryption_key():
    """Retrieves the encryption key from the environment."""
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        logger.critical("ENCRYPTION_KEY environment variable is missing.")
        raise ConfigurationError("ENCRYPTION_KEY must be set in the environment.")
    try:
        return key.encode()
    except Exception as e:
        raise ConfigurationError(f"ENCRYPTION_KEY is not a valid format: {e}")