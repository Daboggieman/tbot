from cryptography.fernet import Fernet
import os
import logging

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_key():
    """
    Generates a new Fernet encryption key.
    This key should be securely stored and used for encryption/decryption.
    """
    key = Fernet.generate_key()
    logger.info("Generated a new Fernet key. Store this securely!")
    return key.decode() # Return as string for easier storage/use in env vars

def encrypt_message(message, key):
    """
    Encrypts a message using the provided Fernet key.
    Args:
        message (str): The message to encrypt.
        key (bytes): The Fernet key (as bytes).
    Returns:
        bytes: The encrypted message.
    """
    f = Fernet(key)
    encrypted_message = f.encrypt(message.encode())
    logger.info("Message encrypted.")
    return encrypted_message

def decrypt_message(encrypted_message, key):
    """
    Decrypts an encrypted message using the provided Fernet key.
    Args:
        encrypted_message (bytes): The encrypted message.
        key (bytes): The Fernet key (as bytes).
    Returns:
        str: The decrypted message.
    """
    f = Fernet(key)
    decrypted_message = f.decrypt(encrypted_message).decode()
    logger.info("Message decrypted.")
    return decrypted_message

def get_encryption_key():
    """
    Retrieves the encryption key from environment variables.
    Raises an error if the key is not found.
    """
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        logger.error("ENCRYPTION_KEY environment variable not set. Cannot perform encryption/decryption.")
        raise ValueError("ENCRYPTION_KEY environment variable not set.")
    return key

if __name__ == "__main__":
    # Example Usage:
    # 1. Generate a key (do this ONCE and store it securely, e.g., in your .env or docker-compose.yml)
    #    key_str = generate_key()
    #    print(f"Generated Key: {key_str}")

    # 2. Use the generated key to encrypt a sensitive message
    #    # Replace with your actual generated key
    #    my_key_str = "YOUR_GENERATED_FERNET_KEY_HERE"
    #    my_key_bytes = my_key_str.encode()
    #    sensitive_data = "my_secret_password_123"
    #    encrypted_data = encrypt_message(sensitive_data, my_key_bytes)
    #    print(f"Encrypted Data: {encrypted_data}")

    # 3. Decrypt the message using the same key
    #    decrypted_data = decrypt_message(encrypted_data, my_key_bytes)
    #    print(f"Decrypted Data: {decrypted_data}")

    # To test with environment variable:
    # Set ENCRYPTION_KEY in your shell before running this script:
    # export ENCRYPTION_KEY="YOUR_GENERATED_FERNET_KEY_HERE" (Linux/macOS)
    # $env:ENCRYPTION_KEY="YOUR_GENERATED_FERNET_KEY_HERE" (PowerShell)
    # set ENCRYPTION_KEY="YOUR_GENERATED_FERNET_KEY_HERE" (CMD)
    # Then run: python security_utils.py
    try:
        key_from_env_str = get_encryption_key()
        key_from_env_bytes = key_from_env_str.encode()
        print(f"Key retrieved from environment: {key_from_env_str[:5]}...") # Print first 5 chars for verification

        test_message = "This is a test secret."
        encrypted_test = encrypt_message(test_message, key_from_env_bytes)
        print(f"Encrypted test message: {encrypted_test}")

        decrypted_test = decrypt_message(encrypted_test, key_from_env_bytes)
        print(f"Decrypted test message: {decrypted_test}")
        assert test_message == decrypted_test
        print("Encryption/Decryption test successful using environment key.")

    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")