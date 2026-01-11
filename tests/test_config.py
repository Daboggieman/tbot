import pytest
from bot.config import Config, CriticalConfigurationError
from bot.security_utils import encrypt_message

def test_config_load_success(monkeypatch):
    key = "v-X-m8D3_S8-pX-_s-X-m8D3_S8-pX-_s-X-m8D3_S8=" # 32-byte key for Fernet
    monkeypatch.setenv("ENCRYPTION_KEY", key)
    
    # Encrypt some values for the test
    enc_user = encrypt_message("test_user", key)
    enc_pass = encrypt_message("test_pass", key)
    enc_token = encrypt_message("test_token", key)
    enc_account = encrypt_message("123456", key)
    
    monkeypatch.setenv("ENCRYPTED_BROKER_USER", enc_user)
    monkeypatch.setenv("ENCRYPTED_BROKER_PASS", enc_pass)
    monkeypatch.setenv("ENCRYPTED_INFLUXDB_TOKEN", enc_token)
    monkeypatch.setenv("ENCRYPTED_MT5_ACCOUNT", enc_account)
    monkeypatch.setenv("ENCRYPTED_MT5_PASSWORD", enc_pass)
    
    monkeypatch.setenv("POSTGRES_USER", "pg_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pg_pass")
    monkeypatch.setenv("MT5_SERVER", "test_server")

    config = Config.load_from_env()
    
    assert config.BROKER_USER == "test_user"
    assert config.BROKER_PASS == "test_pass"
    assert config.PG_USER == "pg_user"
    assert config.MT5_ACCOUNT == "123456"

def test_config_missing_env(monkeypatch):
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    with pytest.raises(CriticalConfigurationError):
        Config.load_from_env()

def test_config_invalid_decryption(monkeypatch):
    key = "v-X-m8D3_S8-pX-_s-X-m8D3_S8-pX-_s-X-m8D3_S8="
    monkeypatch.setenv("ENCRYPTION_KEY", key)
    monkeypatch.setenv("ENCRYPTED_BROKER_USER", "invalid_base64")
    
    with pytest.raises(CriticalConfigurationError, match="Failed to decrypt"):
        Config.load_from_env()
