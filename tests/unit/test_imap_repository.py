# SPDX-FileCopyrightText: 2023 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0

import ssl
import unittest
from unittest import mock

from laelaps.imap_repository import IMAPRepository


@mock.patch("laelaps.imap_repository.aioimaplib.IMAP4_SSL")
class TestImapSSLClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        return super().setUp()

    async def test_context_manager(self, mock_client):
        # Arrange
        initialized_mock_client = mock.AsyncMock()
        mock_client.return_value = initialized_mock_client

        user = "USER"
        password = "PASSWORD"
        mailbox = "MAILBOX"
        host = "HOST"
        ssl_context = ssl.create_default_context()

        # Act
        async with IMAPRepository(
            host=host,
            user=user,
            password=password,
            mailbox=mailbox,
            ssl_context=ssl_context,
        ) as imap_client:
            pass

            # Assert
            self.assertEqual(imap_client.mailbox, "MAILBOX")
        mock_client.assert_called_once_with(
            host=host, timeout=30, ssl_context=ssl_context
        )
        initialized_mock_client.wait_hello_from_server.assert_called_once()
        initialized_mock_client.login.assert_awaited_once_with(user, password)
        initialized_mock_client.select.assert_called_once_with(mailbox=mailbox)
        initialized_mock_client.logout.assert_called_once()

    async def test_wait_for_new_email_message(self, mock_client):
        # Arrange
        initialized_mock_client = mock.AsyncMock()
        mock_client.return_value = initialized_mock_client

        user = "USER"
        password = "PASSWORD"
        mailbox = "MAILBOX"
        host = "HOST"
        ssl_context = ssl.create_default_context()

        # Act
        async with IMAPRepository(
            host=host,
            user=user,
            password=password,
            mailbox=mailbox,
            ssl_context=ssl_context,
        ) as imap_client:
            await imap_client.wait_for_new_email_message()

            # Assert
            self.assertEqual(imap_client.mailbox, "MAILBOX")

        mock_client.assert_called_once_with(
            host=host, timeout=30, ssl_context=ssl_context
        )
        initialized_mock_client.idle_done.assert_called_once()
        initialized_mock_client.wait_hello_from_server.assert_called_once()
        initialized_mock_client.login.assert_awaited_once_with(user, password)
        initialized_mock_client.select.assert_called_once_with(mailbox=mailbox)
        initialized_mock_client.logout.assert_called_once()

    async def test_get_uids_new_messages(self, mock_client):
        # Arrange
        initialized_mock_client = mock.AsyncMock()
        mock_client.return_value = initialized_mock_client
        initialized_mock_client.uid_search.return_value = [
            "OK",
            ["a b".encode("utf-8")],
        ]
        user = "USER"
        password = "PASSWORD"
        mailbox = "MAILBOX"
        host = "HOST"
        ssl_context = ssl.create_default_context()

        # Act
        async with IMAPRepository(
            host=host,
            user=user,
            password=password,
            mailbox=mailbox,
            ssl_context=ssl_context,
        ) as imap_client:
            result = await imap_client.get_uids_new_messages()

            # Assert
            self.assertListEqual(result, ["a", "b"])
            self.assertEqual(imap_client.mailbox, "MAILBOX")
        mock_client.assert_called_once_with(
            host=host, timeout=30, ssl_context=ssl_context
        )
        initialized_mock_client.uid_search.assert_called_once()
        initialized_mock_client.wait_hello_from_server.assert_called_once()
        initialized_mock_client.login.assert_awaited_once_with(user, password)
        initialized_mock_client.select.assert_called_once_with(mailbox=mailbox)
        initialized_mock_client.logout.assert_called_once()

    async def test_get_uids_new_messages_no_result(self, mock_client):
        # Arrange
        initialized_mock_client = mock.AsyncMock()
        mock_client.return_value = initialized_mock_client
        initialized_mock_client.uid_search.return_value = [""]
        user = "USER"
        password = "PASSWORD"
        mailbox = "MAILBOX"
        host = "HOST"
        ssl_context = ssl.create_default_context()

        # Act
        async with IMAPRepository(
            host=host,
            user=user,
            password=password,
            mailbox=mailbox,
            ssl_context=ssl_context,
        ) as imap_client:
            result = await imap_client.get_uids_new_messages()

            # Assert
            self.assertIsNone(result)
            self.assertEqual(imap_client.mailbox, "MAILBOX")
        mock_client.assert_called_once_with(
            host=host, timeout=30, ssl_context=ssl_context
        )
        initialized_mock_client.uid_search.assert_called_once()
        initialized_mock_client.wait_hello_from_server.assert_called_once()
        initialized_mock_client.login.assert_awaited_once_with(user, password)
        initialized_mock_client.select.assert_called_once_with(mailbox=mailbox)
        initialized_mock_client.logout.assert_called_once()

    async def test_get_raw_new_email_headers_from_server(self, mock_client):
        # Arrange
        initialized_mock_client = mock.AsyncMock()
        mock_client.return_value = initialized_mock_client
        initialized_mock_client.uid.return_value = ["OK"]
        user = "USER"
        password = "PASSWORD"
        mailbox = "MAILBOX"
        host = "HOST"
        ssl_context = ssl.create_default_context()

        # Act
        async with IMAPRepository(
            host=host,
            user=user,
            password=password,
            mailbox=mailbox,
            ssl_context=ssl_context,
        ) as imap_client:
            result = await imap_client.get_raw_new_email_headers_from_server("TEST")

            # Assert
            self.assertListEqual(result, ["OK"])
            self.assertEqual(imap_client.mailbox, "MAILBOX")
        mock_client.assert_called_once_with(
            host=host, timeout=30, ssl_context=ssl_context
        )
        initialized_mock_client.uid.assert_called_once()
        initialized_mock_client.wait_hello_from_server.assert_called_once()
        initialized_mock_client.login.assert_awaited_once_with(user, password)
        initialized_mock_client.select.assert_called_once_with(mailbox=mailbox)
        initialized_mock_client.logout.assert_called_once()

    async def test_get_raw_new_email_headers_from_server_no_result(self, mock_client):
        # Arrange
        initialized_mock_client = mock.AsyncMock()
        mock_client.return_value = initialized_mock_client
        initialized_mock_client.uid.return_value = [""]
        user = "USER"
        password = "PASSWORD"
        mailbox = "MAILBOX"
        host = "HOST"
        ssl_context = ssl.create_default_context()

        # Act
        async with IMAPRepository(
            host=host,
            user=user,
            password=password,
            mailbox=mailbox,
            ssl_context=ssl_context,
        ) as imap_client:
            result = await imap_client.get_raw_new_email_headers_from_server("TEST")

            # Assert
            self.assertIsNone(result)
            self.assertEqual(imap_client.mailbox, "MAILBOX")
        mock_client.assert_called_once_with(
            host=host, timeout=30, ssl_context=ssl_context
        )
        initialized_mock_client.uid.assert_called_once()
        initialized_mock_client.wait_hello_from_server.assert_called_once()
        initialized_mock_client.login.assert_awaited_once_with(user, password)
        initialized_mock_client.select.assert_called_once_with(mailbox=mailbox)
        initialized_mock_client.logout.assert_called_once()

    async def test_move_email_to_folder(self, mock_client):
        # Arrange
        initialized_mock_client = mock.AsyncMock()
        mock_client.return_value = initialized_mock_client

        user = "USER"
        password = "PASSWORD"
        mailbox = "MAILBOX"
        host = "HOST"
        ssl_context = ssl.create_default_context()

        # Act
        async with IMAPRepository(
            host=host,
            user=user,
            password=password,
            mailbox=mailbox,
            ssl_context=ssl_context,
        ) as imap_client:
            await imap_client.move_email_to_folder("TEST", "TEST_FOLDER")

            # Assert
            self.assertEqual(imap_client.mailbox, "MAILBOX")
        mock_client.assert_called_once_with(
            host=host, timeout=30, ssl_context=ssl_context
        )
        initialized_mock_client.uid.assert_called_once()
        initialized_mock_client.wait_hello_from_server.assert_called_once()
        initialized_mock_client.login.assert_awaited_once_with(user, password)
        initialized_mock_client.select.assert_called_once_with(mailbox=mailbox)
        initialized_mock_client.logout.assert_called_once()
