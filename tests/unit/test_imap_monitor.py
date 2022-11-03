# SPDX-FileCopyrightText: 2022 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0

"""Unit tests for imap_monitor.py"""
import asyncio
import unittest
from datetime import datetime
from unittest import mock

from laelaps.email_headers_models import AuthenticationResult, EmailHeaders, Transaction
from laelaps.imap_monitor import SignalHandler, decide_target_folder, idle_loop, main


class TestSignalHandler(unittest.TestCase):
    def setUp(self) -> None:
        self.signal_handler = SignalHandler()
        return super().setUp()

    def test_exit_gracefully(self):
        # Arrange
        mock_signum = 1
        mock_frame = mock.MagicMock()

        # Act
        self.signal_handler._exit_gracefully(mock_signum, mock_frame)

        # Assert
        self.assertEqual(self.signal_handler._keep_monitoring, False)

    def test_keep_monitoring(self):
        # Assert
        self.assertEqual(self.signal_handler.keep_monitoring(), True)


@mock.patch("laelaps.imap_monitor.DatabaseRepository.get_allowed_domains")
class TestDecideTargetFolder(unittest.TestCase):
    def test_decide_target_folder_happy_flow(self, db_mock):
        # Arange
        db_mock.return_value = ["from.com"]
        test_headers = EmailHeaders(
            to_address=["test@test.com"],
            from_address="from@from.com",
            authentication_results=AuthenticationResult(
                dkim="none", spf="none", dmarc="none"
            ),
            bcc_address=[],
            cc_address=[],
            recieved=[
                Transaction(
                    from_domain="from.com",
                    to_address="test@test.com",
                    tls=True,
                    timestamp=datetime(2022, 2, 3, 13, 23, 15),
                )
            ],
        )

        # Act
        result = decide_target_folder(
            test_headers,
            config={
                "imap": {},
                "encryption": {"key": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
                "user": {
                    "own_domains": ["test.com"],
                    "target_folder_verified": "INBOX",
                },
            },
        )

        # Assert
        self.assertEqual(result, "INBOX")

    def test_decide_target_folder_failed_validation(self, db_mock):
        # Arange
        db_mock.return_value = []
        test_headers = EmailHeaders(
            to_address=["test@test.com"],
            from_address="srthsrthsrthsrth@notvalidsrthsrthse4rtsysrtjrt.com",
            authentication_results=AuthenticationResult(
                dkim="none", spf="none", dmarc="none"
            ),
            bcc_address=[],
            cc_address=[],
            recieved=[
                Transaction(
                    from_domain="from.com",
                    to_address="test@test.com",
                    tls=True,
                    timestamp=datetime(2022, 2, 3, 13, 23, 15),
                )
            ],
        )

        # Act
        result = decide_target_folder(
            test_headers,
            config={
                "imap": {},
                "encryption": {"key": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
                "user": {
                    "own_domains": ["test.com"],
                    "target_folder_failed_validation": "Inbox/FailedValidation",
                },
            },
        )

        # Assert
        self.assertEqual(result, "Inbox/FailedValidation")


@mock.patch("laelaps.imap_monitor.DatabaseRepository.get_allowed_domains")
@mock.patch("laelaps.imap_monitor.EmailHeadersParser.parse")
@mock.patch("laelaps.imap_monitor.structlog")
@mock.patch("laelaps.email_headers_parser.BytesHeaderParser")
@mock.patch("laelaps.imap_repository.aioimaplib.IMAP4_SSL")
@mock.patch("laelaps.imap_monitor.asyncio.wait_for", new_callable=mock.AsyncMock)
@mock.patch("laelaps.imap_monitor.SignalHandler")
class TestIDLELoop(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        return super().setUp()

    async def test_idle_loop(
        self,
        signal_handler_mock,
        asyncio_mock,
        mock_client,
        bytes_parser_mock,
        structlog_mock,
        email_headers_parser_mock,
        db_mock,
    ):
        # Arrange
        db_mock.return_value = []
        initialized_mock_client = mock.AsyncMock()
        mock_client.return_value = initialized_mock_client

        mock_future = asyncio.Future()
        mock_future.set_result("END")

        initialized_mock_client.idle_start.return_value = mock_future
        initialized_mock_client.uid_search.return_value = [
            "OK",
            ["a b".encode("utf-8")],
        ]
        initialized_mock_client.uid.return_value = [
            "OK",
            ["a b"],
        ]
        email_headers_parser_mock.return_value = EmailHeaders(
            to_address=["test@test.com"],
            from_address="from@from.com",
            authentication_results=AuthenticationResult(
                dkim="none", spf="none", dmarc="none"
            ),
            bcc_address=[],
            cc_address=[],
            recieved=[
                Transaction(
                    from_domain="from.com",
                    to_address="test@test.com",
                    tls=True,
                    timestamp=datetime(2022, 2, 3, 13, 23, 15),
                )
            ],
        )

        initialized_signal_handler = mock.MagicMock()
        signal_handler_mock.return_value = initialized_signal_handler

        initialized_signal_handler.keep_monitoring.side_effect = [True, False]

        initialized_bytes_parser_mock = mock.MagicMock()
        bytes_parser_mock.return_value = initialized_bytes_parser_mock

        logger_mock = mock.MagicMock()
        structlog_mock.getLogger.return_value = logger_mock

        user = "USER"
        password = "PASSWORD"
        mailbox = "MAILBOX"
        host = "HOST"

        # Act
        await idle_loop(
            host=host,
            user=user,
            password=password,
            mailbox=mailbox,
            config={
                "imap": {},
                "encryption": {"key": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
                "user": {
                    "own_domains": ["test.com"],
                    "target_folder_failed_validation": "Failed",
                },
            },
        )

        # Assert
        initialized_mock_client.wait_hello_from_server.assert_called_once()
        initialized_mock_client.login.assert_awaited_once_with(user, password)
        initialized_mock_client.select.assert_called_once_with(mailbox=mailbox)
        initialized_mock_client.logout.assert_called_once()


@mock.patch("laelaps.imap_monitor.toml")
@mock.patch("laelaps.imap_monitor.asyncio.run")
class TestMain(unittest.TestCase):
    def test_main(self, run_mock, toml_mock):
        # Arrange
        toml_mock.load.return_value = {
            "imap": {
                "host": "HOST",
                "user": "USER",
                "password": "PASSWORD",
                "mailbox": "MAILBOX",
            }
        }

        # Act
        main()

        # Assert
        toml_mock.load.assert_called()
