# SPDX-FileCopyrightText: 2024 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0

import unittest
from datetime import datetime, timezone

from laelaps.email_headers_models import (
    AuthenticationResult,
    EmailHeaders,
    Result,
    Transaction,
)


class TestModels(unittest.TestCase):
    def test_authentication_result(self):
        # Arrange
        test_authentication_result = AuthenticationResult(
            spf="none", dkim="pass", dmarc="fail"
        )

        # Act
        dkim = test_authentication_result["dkim"]

        # Assert
        self.assertEqual(dkim, Result.PASSED)

    def test_transaction(self):
        # Arrange
        test_transaction = Transaction(
            from_domain="from.com",
            to_address="hello@hello.com",
            tls=True,
            timestamp=datetime(2022, 2, 2, 12, 12),
        )

        # Act
        tls = test_transaction["tls"]

        # Assert
        self.assertTrue(tls)

    def test_email_headers(self):
        # Arrange
        test_email_headers = EmailHeaders(
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
        from_address = test_email_headers["from_address"]

        # Assert
        self.assertEqual(from_address, "from@from.com")
