import pytest
from bot.security_utils import encrypt_message, decrypt_message, SecurityError, DecryptionError

def test_encryption_decryption_success():
    key = "v-X-m8D3_S8-pX-_s-X-m8D3_S8-pX-_s-X-m8D3_S8="
    message = "Hello World"
    
    encrypted = encrypt_message(message, key)
    assert encrypted != message
    
    decrypted = decrypt_message(encrypted, key.encode())
    assert decrypted == message

def test_decryption_failure():
    key = "v-X-m8D3_S8-pX-_s-X-m8D3_S8-pX-_s-X-m8D3_S8="
    wrong_key = "v-X-m8D3_S8-pX-_s-X-m8D3_S8-pX-_s-X-m8D3_S9="
    message = "Hello World"
    
    encrypted = encrypt_message(message, key)
    
    with pytest.raises(DecryptionError):
        decrypt_message(encrypted, wrong_key.encode())

def test_invalid_base64_decryption():
    key = "v-X-m8D3_S8-pX-_s-X-m8D3_S8-pX-_s-X-m8D3_S8="
    with pytest.raises(DecryptionError):
        decrypt_message("invalid_base64", key.encode())
