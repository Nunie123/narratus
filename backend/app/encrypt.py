import aws_encryption_sdk
from backend.app import aws_key_id

# AWS credentials must be provided in config file.  See: https://boto3.readthedocs.io/en/latest/guide/configuration.html
kms_key_provider = aws_encryption_sdk.KMSMasterKeyProvider(
    key_ids=[aws_key_id]
)


def encrypt_with_aws(plaintext):
    ciphertext, encryptor_header = aws_encryption_sdk.encrypt(
        source=plaintext,
        key_provider=kms_key_provider
    )
    return ciphertext


def decrypt_with_aws(ciphertext):
    plaintext, decryptor_header = aws_encryption_sdk.decrypt(
        source=ciphertext,
        key_provider=kms_key_provider
    )
    return plaintext.decode('utf-8')
