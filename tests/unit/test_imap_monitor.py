# SPDX-FileCopyrightText: 2024 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0

"""Unit tests for imap_monitor.py"""
import asyncio
import unittest
from datetime import datetime
from unittest import mock

from pydantic import SecretStr

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
        # Arrange
        db_mock.return_value = ["from.com"]
        test_headers = EmailHeaders(
            to_address=["test@test.com"],
            from_address="from@from.com",
            authentication_results=AuthenticationResult(
                dkim="none", spf="none", dmarc="none"
            ),
            bcc_address=[],
            cc_address=[],
            received=[
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
                "encryption": {"key": SecretStr("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")},
                "user": {
                    "own_domains": ["test.com"],
                    "target_folder_verified": "INBOX",
                },
            },
        )

        # Assert
        self.assertEqual(result, "INBOX")

    def test_decide_target_folder_failed_validation(self, db_mock):
        # Arrange
        db_mock.return_value = []
        test_headers = EmailHeaders(
            to_address=["test@test.com"],
            from_address="srthsrthsrthsrth@notvalidsrthsrthse4rtsysrtjrt.com",
            authentication_results=AuthenticationResult(
                dkim="none", spf="none", dmarc="none"
            ),
            bcc_address=[],
            cc_address=[],
            received=[
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
                "encryption": {"key": SecretStr("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")},
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
            received=[
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

        username = "USER"
        password = SecretStr("PASSWORD")
        mailbox = "MAILBOX"
        host = "HOST"

        # Act
        await idle_loop(
            host=host,
            username=username,
            password=password,
            mailbox=mailbox,
            config={
                "imap": {},
                "encryption": {"key": SecretStr("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")},
                "user": {
                    "own_domains": ["test.com"],
                    "target_folder_failed_validation": "Failed",
                },
            },
        )

        # Assert
        initialized_mock_client.wait_hello_from_server.assert_called_once()
        initialized_mock_client.login.assert_awaited_once_with(
            username, password.get_secret_value()
        )
        initialized_mock_client.select.assert_called_once_with(mailbox=mailbox)
        initialized_mock_client.logout.assert_called_once()


@mock.patch("laelaps.imap_monitor.asyncio.run")
class TestMain(unittest.TestCase):
    @mock.patch("laelaps.imap_monitor.toml")
    def test_main_config_file(self, toml_mock, run_mock):
        # Arrange
        toml_mock.load.return_value = {
            "imap": {
                "host": "HOST",
                "username": "USER",
                "password": "PASSWORD",
                "mailbox": "MAILBOX",
            },
            "user": {
                "own_domains": ["test.com"],
                "target_folder_failed_validation": "Failed",
                "target_folder_verified": "Verified",
            },
            "encryption": {"key": "asdasdasdasdasdasdasdasdasdasd"},
        }

        # Act
        main()

        # Assert
        toml_mock.load.assert_called()
        run_mock.assert_called()

    @mock.patch("laelaps.imap_monitor.idle_loop")
    def test_main_no_environment_variables_and_no_config_file(
        self, run_mock, ideloop_mock
    ):
        # Act
        main()

        # Assert
        run_mock.assert_not_called()

    @mock.patch("laelaps.imap_monitor.ConfigModel")
    def test_main_no_config_file(self, config_model_mock, run_mock):
        # Arrange
        init_config_mock = mock.MagicMock()

        config_model_mock.side_effect = [init_config_mock]

        init_config_mock.model_dump.return_value = {
            "imap": {
                "host": "HOST",
                "username": "USER",
                "password": "PASSWORD",
                "mailbox": "MAILBOX",
            },
            "user": {
                "own_domains": ["test.com"],
                "target_folder_failed_validation": "Failed",
                "target_folder_verified": "Verified",
            },
            "encryption": {"key": "asdasdasdasdasdasdasdasdasdasd"},
        }

        # Act
        main()

        # Assert
        config_model_mock.assert_called()
        run_mock.assert_called()
