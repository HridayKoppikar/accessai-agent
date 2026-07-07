"""
Encryption utilities for AccessAI.

Provides AES-256 encryption for user health data and other sensitive information.
"""

import os
import base64
import json
from typing import Any, Dict
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes
from Cryptodome.Protocol.KDF import PBKDF2

# Encryption key derivation (in production, use secure key management)
ENCRYPTION_SALT = b'accessai_health_data_salt_v1'
AES_BLOCK_SIZE = 16


def encrypt_data(data: Dict[str, Any], user_id: str) -> str:
    """Encrypt sensitive user data using AES-256.

    Args:
        data: Dictionary containing sensitive data to encrypt
        user_id: User identifier for key derivation

    Returns:
        Base64 encoded encrypted string
    """
    # Convert data to JSON string
    data_json = json.dumps(data, sort_keys=True)
    data_bytes = data_json.encode('utf-8')

    # Derive encryption key from user_id
    key = PBKDF2(user_id, ENCRYPTION_SALT, dkLen=32, count=100000)

    # Generate random IV
    iv = get_random_bytes(AES_BLOCK_SIZE)

    # Create cipher and encrypt
    cipher = AES.new(key, AES.MODE_CBC, iv)

    # Pad data to block size
    padding_length = AES_BLOCK_SIZE - (len(data_bytes) % AES_BLOCK_SIZE)
    padded_data = data_bytes + bytes([padding_length] * padding_length)

    # Encrypt
    encrypted = cipher.encrypt(padded_data)

    # Combine IV and encrypted data, encode as base64
    result = base64.b64encode(iv + encrypted).decode('utf-8')

    return result


def decrypt_data(encrypted_data: str, user_id: str) -> Dict[str, Any]:
    """Decrypt user data using AES-256.

    Args:
        encrypted_data: Base64 encoded encrypted string
        user_id: User identifier for key derivation

    Returns:
        Decrypted data dictionary
    """
    # Decode base64
    decoded = base64.b64decode(encrypted_data)

    # Extract IV and encrypted data
    iv = decoded[:AES_BLOCK_SIZE]
    encrypted = decoded[AES_BLOCK_SIZE:]

    # Derive encryption key
    key = PBKDF2(user_id, ENCRYPTION_SALT, dkLen=32, count=100000)

    # Create cipher and decrypt
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_padded = cipher.decrypt(encrypted)

    # Remove and validate PKCS#7 padding. A corrupt or tampered ciphertext can
    # produce an out-of-range padding byte that would silently slice the wrong
    # number of bytes (or crash with a negative slice). Validate explicitly.
    if not decrypted_padded:
        raise ValueError("Decryption failed: empty ciphertext")
    padding_length = decrypted_padded[-1]
    if padding_length < 1 or padding_length > AES_BLOCK_SIZE:
        raise ValueError("Decryption failed: invalid padding (corrupt or wrong key)")
    # Every padding byte must equal padding_length (PKCS#7 spec)
    if decrypted_padded[-padding_length:] != bytes([padding_length]) * padding_length:
        raise ValueError("Decryption failed: invalid padding (corrupt or wrong key)")
    decrypted = decrypted_padded[:-padding_length]

    # Parse JSON
    data = json.loads(decrypted.decode('utf-8'))

    return data


def encrypt_health_data(health_profile: Dict[str, Any], user_id: str) -> str:
    """Encrypt health data specifically (allergies, medications, etc.).

    Args:
        health_profile: User's health information
        user_id: User identifier

    Returns:
        Encrypted health data string
    """
    # Health data encryption with additional metadata
    encrypted_payload = {
        'version': '1.0',
        'encrypted_at': '2026-07-02T00:00:00Z',
        'data': health_profile
    }

    return encrypt_data(encrypted_payload, user_id)


def decrypt_health_data(encrypted_health_data: str, user_id: str) -> Dict[str, Any]:
    """Decrypt health data and validate integrity.

    Args:
        encrypted_health_data: Encrypted health data string
        user_id: User identifier

    Returns:
        Decrypted health profile
    """
    payload = decrypt_data(encrypted_health_data, user_id)

    # Validate version
    if payload.get('version') != '1.0':
        raise ValueError("Unsupported encryption version")

    return payload.get('data', {})


def hash_sensitive_data(data: str, salt: str = None) -> str:
    """Create hash of sensitive data for comparison without storing raw.

    Args:
        data: Sensitive data to hash
        salt: Optional salt value

    Returns:
        Hashed string
    """
    import hashlib

    if salt is None:
        salt = ENCRYPTION_SALT.decode('utf-8')

    # Use SHA-256 with PBKDF2
    hash_value = PBKDF2(data, salt, dkLen=64, count=100000)
    return base64.b64encode(hash_value).decode('utf-8')


def is_encrypted(data: str) -> bool:
    """Check if data appears to be encrypted.

    Args:
        data: String to check

    Returns:
        True if data appears encrypted
    """
    try:
        decoded = base64.b64decode(data)
        # Encrypted data should be reasonably long and valid base64
        return len(decoded) > 32
    except Exception:
        return False