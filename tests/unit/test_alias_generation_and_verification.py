# SPDX-FileCopyrightText: 2024 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0

"""Unit tests for generate_sieve_filter.py"""
import datetime
import unittest

import email_validator
import numpy as np

from laelaps.alias_generation_and_verification import (
    AliasGenerator,
    AliasInformationExtractor,
)


class TestAliasGeneration(unittest.TestCase):
    def setUp(self) -> None:
        self.key: str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        self.own_domain: str = "test.com"

        self.alias_generator = AliasGenerator(self.key, self.own_domain)
        return super().setUp()

    def test_generate_alias(self):
        # Arrange
        other_domain: str = "other.com"

        # Act
        alias, alias_verification = self.alias_generator.generate_alias(other_domain)

        # Assert
        self.assertEqual(alias.split("-")[0], "other")
        self.assertEqual(alias.split("@")[1], self.own_domain)
        self.assertEqual(alias_verification.as_dict()["original"], alias)
        self.assertIsInstance(alias_verification, email_validator.ValidatedEmail)

    def test_validate_email(self):
        # Arrange
        email = "@@@@"

        # Act
        result = self.alias_generator._validate_email(email)

        # Assert
        self.assertIsNone(result)


class TestAliasVerification(unittest.TestCase):
    def setUp(self) -> None:
        self.key: str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        self.own_domain: str = "test.com"
        self.alias_information_extractor = AliasInformationExtractor(
            self.key, self.own_domain
        )
        return super().setUp()

    def test_extract_and_validate_information_happy_flow(self):
        # Arrange
        alias: str = "other-0EFCF5804239mM6G490b6pGJAG3uCfBCVA@test.com"

        # Act
        verification_result = (
            self.alias_information_extractor.extract_and_validate_information(alias)
        )

        # Assert
        self.assertEqual(
            verification_result,
            {
                "checked_alias": "other-0EFCF5804239mM6G490b6pGJAG3uCfBCVA@test.com",
                "generation_date": datetime.date(2022, 9, 27),
                "passed_signature_verification": True,
            },
        )

    def test_extract_and_validate_information_hash_does_not_match(self):
        # Arrange
        alias: str = "otger-0EFCF5804239mM6G490b6pGJAG3uCfBCVA@test.com"

        # Act
        verification_result = (
            self.alias_information_extractor.extract_and_validate_information(alias)
        )

        # Assert
        self.assertEqual(
            verification_result,
            {
                "checked_alias": "otger-0EFCF5804239mM6G490b6pGJAG3uCfBCVA@test.com",
                "generation_date": np.nan,
                "passed_signature_verification": False,
            },
        )

    def test_extract_and_validate_information_fake_address(self):
        # Arrange
        alias: str = "other-EAC3B_97A76ACdpYMcGNK24fAgyHTruOf@test.com"

        # Act
        verification_result = (
            self.alias_information_extractor.extract_and_validate_information(alias)
        )

        # Assert
        self.assertEqual(
            verification_result,
            {
                "checked_alias": "other-EAC3B_97A76ACdpYMcGNK24fAgyHTruOf@test.com",
                "generation_date": np.nan,
                "passed_signature_verification": False,
            },
        )

    def test_extract_and_validate_information_undecodable_address(self):
        # Arrange
        alias: str = "aaaaa-EAC3B_87A76ACdpYMcGNK24fAgyHTruOfh@test.com"

        # Act
        verification_result = (
            self.alias_information_extractor.extract_and_validate_information(alias)
        )

        # Assert
        self.assertEqual(
            verification_result,
            {
                "checked_alias": "aaaaa-EAC3B_87A76ACdpYMcGNK24fAgyHTruOfh@test.com",
                "generation_date": np.nan,
                "passed_signature_verification": False,
            },
        )

    def test_extract_and_validate_information_wrong_password(self):
        # Arrange
        alias: str = "aaaaa-EAC3B_87A76ACdpYMcGNK24fAgyHTruOfh@test.com"
        self.alias_information_extractor = AliasInformationExtractor(
            "wrong-key", self.own_domain
        )

        # Act
        verification_result = (
            self.alias_information_extractor.extract_and_validate_information(alias)
        )

        # Assert
        self.assertEqual(
            verification_result,
            {
                "checked_alias": alias,
                "generation_date": np.nan,
                "passed_signature_verification": False,
            },
        )

    def test_extract_and_validate_old_address(self):
        # Arrange
        alias: str = "aaaaa-EAC3B_87A76ACdpYMcGNK24-AgyHTruOfh@test.com"
        self.alias_information_extractor = AliasInformationExtractor(
            "wrong-key", self.own_domain
        )

        # Act
        verification_result = (
            self.alias_information_extractor.extract_and_validate_information(alias)
        )

        # Assert
        self.assertEqual(
            verification_result,
            {
                "checked_alias": alias,
                "generation_date": np.nan,
                "passed_signature_verification": False,
            },
        )
