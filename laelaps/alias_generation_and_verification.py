# SPDX-FileCopyrightText: 2023 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0
"""Functionality for generating aliases.

Library of functions and classes to enable alias generation

"""

import hashlib
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import date, datetime

import email_validator
import numpy as np
import structlog
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from email_validator import EmailNotValidError, caching_resolver, validate_email

# Global config test
MAXIMUM_LENGTH: int = 40  # Maximum length of the local part of the alias
NUMBER_OF_HASH_DIGITS: int = (
    8  # Number of digits of the hash digest to include in the encrypted part
)
ENCRYPTED_PART_LENGTH_AFTER_ENCRYPTION: int = (
    22  # After encryption the encrypted part is encoded in base 64 (URI safe)
)
ENCRYPTED_PART_LENGTH_BEFORE_ENCRYPTION: int = (
    16  # Length of encrypted part string before encryption (ascii encoded)
)
INITIALIZATION_VECTOR_LENGTH: int = 16  # Length of initialization vector

TEXT_ENCODING: str = "utf-8"  # Encoding that is used for hashes and encryption


class AliasBaseClass:
    """Base class for an alias."""

    def __init__(self, password: str, own_domain: str = ""):
        """Initialize object.

        :param password: user password
        :param own_domain: own domain of the user, defaults to ""

        """
        self.own_domain = own_domain
        self.key = password
        self.logger = structlog.getLogger(self.__class__.__name__)

    @staticmethod
    def _hash(to_be_hashed: str) -> str:
        return hashlib.sha256(to_be_hashed.encode(TEXT_ENCODING)).hexdigest()

    def _validate_email(self, alias: str) -> email_validator.ValidatedEmail | None:
        """Check whether string complies with email format standards.

        :param alias: email address to be checked
        :return: report with the result

        """
        resolver = caching_resolver(timeout=10)
        valid = None

        try:
            # validate
            valid = validate_email(alias, dns_resolver=resolver)
        except EmailNotValidError as exception:
            # email is not valid
            self.logger.exception(
                "Alias is not a valid email address.", alias=alias, exception=exception
            )
        return valid


class AliasGenerator(AliasBaseClass):
    """Generates an alias base on external domain."""

    def generate_alias(
        self, other_domain: str
    ) -> tuple[str, email_validator.ValidatedEmail]:
        """Generate an alias for an external domain.

        :param other_domain: external domain for which the alias has to be generated
        :return: the alias and a validation result

        """
        other_domain_tag = other_domain.split(".")[-2] + "-"

        date_int = str(datetime.utcnow().date()).replace("-", "")

        desired_length_random_part = (
            MAXIMUM_LENGTH
            - ENCRYPTED_PART_LENGTH_AFTER_ENCRYPTION
            - len(other_domain_tag)  # Encrypted part
        )

        random_part = self._generate_random_part(desired_length_random_part)

        to_be_hashed = other_domain_tag + date_int + random_part

        hashed = self._hash(to_be_hashed)

        to_be_encrypted = date_int + hashed[:NUMBER_OF_HASH_DIGITS]

        encrypted = self._encrypt(
            to_be_encrypted,
            (other_domain_tag + random_part)[:INITIALIZATION_VECTOR_LENGTH],
        )

        alias = other_domain_tag + random_part + encrypted + "@" + self.own_domain

        valid = self._validate_email(alias)

        return alias, valid

    def _encrypt(self, to_be_encrypted: str, initialization_vector: str) -> str:
        """Encrypt a string with a given initialization vector.

        :param to_be_encrypted: string to be encrypts
        :param initialization_vector: initialization vector
        :return: encrypted string

        """
        cipher = Cipher(
            algorithms.AES(self.key.encode("utf-8")),
            modes.CBC(initialization_vector.encode(TEXT_ENCODING)),
        )
        encryptor = cipher.encryptor()
        encrypted_text = (
            encryptor.update(to_be_encrypted.encode(TEXT_ENCODING))
            + encryptor.finalize()
        )
        return urlsafe_b64encode(encrypted_text).decode(TEXT_ENCODING).rstrip("=")

    @staticmethod
    def _generate_random_part(desired_length: int) -> str:
        """Generate the random part of the alias.

        :param desired_length: desired length of the random part
        :return: string with random symbols of desired length

        """
        return "".join(
            secrets.choice("ABCDEF01234356789_") for i in range(desired_length)
        )


class AliasInformationExtractor(AliasBaseClass):
    """Extracts alias information from a previously generated alias."""

    def extract_and_validate_information(self, alias: str) -> dict:
        """Extract and validates information of a previously generated alias.

        :param alias: alias to be decrypted
        :return: Extracted information that is contained in the alias

        """
        encrypted = alias.split("@")[0]

        to_decrypt = encrypted[-ENCRYPTED_PART_LENGTH_AFTER_ENCRYPTION:]

        # Check for old style aliassses, they cannot be decrypted
        if "-" in to_decrypt:
            return {
                "checked_alias": alias,
                "generation_date": np.nan,
                "passed_signature_verification": False,
            }

        # Return not validated when decryption failed
        try:
            decrypted = self._decrypt(to_decrypt, alias[:INITIALIZATION_VECTOR_LENGTH])
        except ValueError as exception:
            self.logger.error(
                "Could not decrypt alias, please check if you are using the correct password!",
                exception_name=exception.__class__.__name__,
            )
            return {
                "checked_alias": alias,
                "generation_date": np.nan,
                "passed_signature_verification": False,
            }

        check_hash = decrypted[-NUMBER_OF_HASH_DIGITS:]

        date_int = decrypted[
            : (ENCRYPTED_PART_LENGTH_BEFORE_ENCRYPTION - NUMBER_OF_HASH_DIGITS)
        ]

        to_be_hashed = (
            encrypted[:-ENCRYPTED_PART_LENGTH_AFTER_ENCRYPTION].split("-")[0]
            + "-"
            + date_int
            + encrypted[:-ENCRYPTED_PART_LENGTH_AFTER_ENCRYPTION].split("-")[1]
        )

        hashed = self._hash(to_be_hashed)[:NUMBER_OF_HASH_DIGITS]

        if check_hash == hashed:
            generation_date: date | float = datetime.strptime(date_int, "%Y%m%d").date()
            validation = True
        else:
            generation_date = np.nan
            validation = False

        return {
            "checked_alias": alias,
            "generation_date": generation_date,
            "passed_signature_verification": validation,
        }

    def _decrypt(self, to_be_decrypted_text: str, initialization_vector: str) -> str:
        encrypted_bytes = self._base64_decode_auto_padded(to_be_decrypted_text)
        cipher = Cipher(
            algorithms.AES(self.key.encode("utf-8")),
            modes.CBC(initialization_vector.encode(TEXT_ENCODING)),
        )
        decryptor = cipher.decryptor()
        plain_text = (decryptor.update(encrypted_bytes) + decryptor.finalize()).decode(
            TEXT_ENCODING
        )
        return plain_text

    @staticmethod
    def _base64_decode_auto_padded(base64_string: str) -> bytes:
        return urlsafe_b64decode(base64_string + "=="[: 3 - len(base64_string) % 3])
