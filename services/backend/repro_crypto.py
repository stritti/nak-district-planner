import base64
import hashlib
import json
from cryptography.fernet import Fernet


def get_fernet(secret_key: str) -> Fernet:
    raw_key = hashlib.sha256(secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw_key))


def test_crypto():
    key1 = "my-secret-key"
    key2 = "my-secret-key-changed"
    data = {"url": "https://example.com"}

    f1 = get_fernet(key1)
    token = f1.encrypt(json.dumps(data).encode()).decode()
    print(f"Token: {token}")

    # Decrypt with same key
    dec1 = json.loads(f1.decrypt(token.encode()))
    print(f"Decrypted with key1: {dec1}")

    # Decrypt with different key
    f2 = get_fernet(key2)
    try:
        f2.decrypt(token.encode())
    except Exception as e:
        print(f"Decrypted with key2 failed as expected: {type(e).__name__}")


if __name__ == "__main__":
    test_crypto()
