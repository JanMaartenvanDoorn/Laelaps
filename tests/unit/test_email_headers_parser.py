# SPDX-FileCopyrightText: 2023 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0

import unittest
from datetime import datetime, timezone
from unittest import mock
from unittest.mock import MagicMock

from laelaps.email_headers_models import AuthenticationResult, EmailHeaders
from laelaps.email_headers_parser import EmailHeadersParser, Transaction

TEST_OWN_DOMAIN = ["owndomain.org"]


class TestEmailHeadersParser(unittest.TestCase):
    def setUp(self) -> None:
        """Setup test database."""
        self.email_header_parser = EmailHeadersParser(TEST_OWN_DOMAIN)
        return super().setUp()

    @mock.patch("laelaps.email_headers_parser.BytesHeaderParser.parsebytes")
    @mock.patch("laelaps.email_headers_parser.EmailHeadersParser._parse_received")
    def test_parse(self, parse_received_mock, bytes_parser_mock):
        # Arrange
        parse_received_mock.return_value = [
            Transaction(
                from_domain="mx.somemailserver.net",
                to_address="hello@hello.com",
                tls=False,
                timestamp=datetime(2022, 9, 23, 13, 18, 48, tzinfo=timezone.utc),
            )
        ]
        bytes_parser_mock.return_value = {
            "Authentication-Results": None,
            "To": "hello@notowndomain.org",
            "From": "from@from.com",
            "Cc": "c@cc.cc",
            "Bcc": "Bcc@bcc.be",
        }

        expected_result = EmailHeaders(
            to_address=[""],
            from_address="from@from.com",
            authentication_results=AuthenticationResult(
                dkim="none", spf="none", dmarc="none"
            ),
            received=[
                Transaction(
                    from_domain="mx.somemailserver.net",
                    to_address="hello@hello.com",
                    timestamp=datetime(2022, 9, 23, 13, 18, 48, tzinfo=timezone.utc),
                    tls=False,
                )
            ],
            cc_address=["c@cc.cc"],
            bcc_address=["Bcc@bcc.be"],
        )

        # Act
        result = self.email_header_parser.parse(MagicMock())

        # Assert
        self.assertEqual(result, expected_result)

    def test_parse_from_address(self):
        # Arrange
        test_message_headers = {"From": "hello@hello.com"}

        # Act
        result = self.email_header_parser._parse_address(test_message_headers, "From")

        # Assert
        self.assertEqual(result, ["hello@hello.com"])

    def test_parse_to_address(self):
        # Arrange
        test_message_headers = {"To": "hello@owndomain.org"}

        # Act
        result = self.email_header_parser._parse_address(test_message_headers, "To")

        # Assert
        self.assertEqual(result, ["hello@owndomain.org"])

    def test_parse_to_address_not_own_domain(self):
        # Arrange
        test_message_headers = {"To": "hello@notowndomain.org"}

        # Act
        result = self.email_header_parser._parse_address(test_message_headers, "To")

        # Assert
        self.assertEqual(result, [""])

    def test_parse_address_no_index(self):
        # Arrange
        test_message_headers = {"From": None}

        # Act
        result = self.email_header_parser._parse_address(test_message_headers, "From")

        # Assert
        self.assertEqual(result, [""])

    def test_parse_cc_address(self):
        # Arrange
        test_message_headers = {"Cc": "hello@anydomain.org"}

        # Act
        result = self.email_header_parser._parse_address(test_message_headers, "Cc")

        # Assert
        self.assertEqual(result, ["hello@anydomain.org"])

    def test_parse_authentication_result_empty_header(self):
        # Arrange
        test_message_headers = {"Authentication-Results": None}
        expected_result = AuthenticationResult(
            **{"dkim": "none", "spf": "none", "dmarc": "none"}
        )
        # Act
        result = self.email_header_parser._parse_authentication_result(
            test_message_headers
        )

        # Assert
        self.assertEqual(result, expected_result)

    def test_parse_authentication_result(self):
        # Arrange
        test_message_headers = {"Authentication-Results": "spf=pass, dkim=fail"}
        expected_result = AuthenticationResult(
            **{"dkim": "fail", "spf": "pass", "dmarc": "none"}
        )
        # Act
        result = self.email_header_parser._parse_authentication_result(
            test_message_headers
        )

        # Assert
        self.assertEqual(result, expected_result)

    def test_parse_received(self):
        # Arrange
        test_message_headers = MagicMock()
        test_message_headers._headers = [
            [
                "Received",
                "from mx.somemailserver.net for <hello@hello.com>; Fri, 23 Sep 2022 13:18:48 +0000",
            ],
            ["Received", "from blablabla ; Fri, 23 Sep 2022 13:18:48 +0000"],
        ]

        expected_result = [
            Transaction(
                from_domain="mx.somemailserver.net",
                to_address="hello@hello.com",
                tls=False,
                timestamp=datetime(2022, 9, 23, 13, 18, 48, tzinfo=timezone.utc),
            ),
            Transaction(
                to_address="unknown",
                tls=False,
                from_domain="blablabla",
                timestamp=datetime(2022, 9, 23, 13, 18, 48, tzinfo=timezone.utc),
            ),
        ]

        # Act
        result = self.email_header_parser._parse_received(test_message_headers)

        # Assert
        self.assertEqual(result, expected_result)

    @mock.patch("laelaps.email_headers_parser.datetime")
    def test_parse_received_unknown_timestamp(self, dt_mock):
        # Arrange

        dt_mock.utcnow = mock.Mock(
            return_value=datetime(2022, 9, 23, 13, 18, 48, tzinfo=timezone.utc)
        )
        test_message_headers = MagicMock()
        test_message_headers._headers = [
            [
                "Received",
                "from mx.somemailserver.net for <hello@hello.com>",
            ],
        ]

        expected_result = [
            Transaction(
                from_domain="mx.somemailserver.net",
                to_address="hello@hello.com",
                tls=False,
                timestamp=datetime(2022, 9, 23, 13, 18, 48, tzinfo=timezone.utc),
            )
        ]

        # Act
        result = self.email_header_parser._parse_received(test_message_headers)

        # Assert
        self.assertEqual(result, expected_result)
