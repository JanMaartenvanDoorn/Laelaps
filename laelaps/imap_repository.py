# SPDX-FileCopyrightText: 2024 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0
"""Defines imap repository."""
import asyncio
import ssl

import structlog
from aioimaplib import aioimaplib

HEADERS_TO_FETCH = {
    "Authentication-Results",
    "Received",
    "From",
    "To",
    "Cc",
    "Bcc",
    "Date",
}


class IMAPRepository:
    """Async context manager for the async imap SSL client.

    This manager logs in to the imap server and selects a folder to monitor. Using this context manager makes sure the
    connection is properly closed off in case of unexpected events.

    """

    def __init__(
        self,
        user: str,
        password: str,
        mailbox: str,
        host: str = "127.0.0.1",
        timeout: float = 30,
        ssl_context: ssl.SSLContext = ssl.create_default_context(),
    ):
        """Initialize context manager.

        :param user: Username to log in to the imap server
        :param password: Password to log in to the imap server
        :param mailbox: Folder that needs to be monitored
        :param host: host of the imap server, defaults to "127.0.0.1"
        :param timeout: timeout in seconds, defaults to 30
        :param ssl_context: SSL Context to be used when connecting to the imap server, defaults to
            ssl.create_default_context()

        """
        self.logger = structlog.getLogger(self.__class__.__name__)
        self.user = user
        self.password = password
        self.mailbox = mailbox
        self.logger.info("Initializing IMAP context.")
        self.imap_client = aioimaplib.IMAP4_SSL(
            host=host, timeout=timeout, ssl_context=ssl_context
        )

    async def wait_for_new_email_message(self) -> asyncio.Future:
        """Wait for new messages using IDLE mode.

        :return: asyncio Future.

        """
        idle = await self.imap_client.idle_start(timeout=5)
        await self.imap_client.wait_server_push()
        self.imap_client.idle_done()
        return idle

    async def get_uids_new_messages(self) -> list[str] | None:
        """Get uids of new messages on the imap server.

        :return: List of uids that are found.

        """
        search_result = await self.imap_client.uid_search("UNSEEN")
        # First entry indicates if search was successful
        # Second entry contains a list of which the first entry contains the results
        # and the second contains information about the search itself.
        if search_result[0] == "OK":
            return search_result[1][0].decode("utf-8").split(" ")
        return None

    async def get_raw_new_email_headers_from_server(
        self, uid: str
    ) -> aioimaplib.Response | None:
        """Get raw email headers for message with specified uid.

        :param uid: Uid of the message
        :return: Raw message headers

        """
        fetched_headers = await self.imap_client.uid(
            "fetch",
            uid,
            f"(BODY.PEEK[HEADER.FIELDS ({' '.join(HEADERS_TO_FETCH)})])",
        )
        if fetched_headers[0] == "OK":
            return fetched_headers
        return None

    async def move_email_to_folder(self, uid: str, target_folder: str) -> None:
        """Move email message with specified uid to target folder.

        :param uid: uid of the email message.
        :param target_folder: Folder on the imap server to which the email message has to be moved.

        """
        await self.imap_client.uid("move", uid, target_folder)

    async def __aenter__(self):
        """Enter context manager.

        Takes care of setting up the IMAP connection and selecting the relevant folder.

        :return: An instance of this class.

        """
        await self.imap_client.wait_hello_from_server()
        await self.imap_client.login(self.user, self.password)
        await self.imap_client.select(mailbox=self.mailbox)
        self.logger.info(
            "Logged in to IMAP server", host=self.imap_client.host, user=self.user
        )
        return self

    async def __aexit__(self, exc_type: type, exc_info: str, stack_info: str) -> None:
        """Exit the context manager.

        This makes sure we properly log out of the server even in case of exceptions.

        :param exc_type: Exception type
        :param exc_info: Exception info
        :param stack_info: Stack trace

        """
        await self.imap_client.logout()
        self.logger.info("Logged out of imap server.")
