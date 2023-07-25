# SPDX-FileCopyrightText: 2023 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0
"""Define email header parser."""
import re
from datetime import datetime
from email.message import Message
from email.parser import BytesHeaderParser

import aioimaplib

from laelaps.email_headers_models import (
    AuthenticationResult,
    EmailHeaders,
    Result,
    Transaction,
)

EMAIL_REGEX = r"""[\w.+-]+@[\w-]+\.[\w.-]+"""
SERVER_SIDE_CHECKS = ["dkim", "spf", "dmarc"]


class EmailHeadersParser:
    """Email header parser.

    This class parses relevant information from the raw header strings to pydantic models to facilitate a well-defined
    informaiton flow within the monitor.

    """

    def __init__(self, own_domains: list[str]) -> None:
        """Initialize the email header parser.

        :param own_domains: A list of domains that are owned by the user to identify the to_address of the user in case
            of multiple to_addresses.

        """
        self.own_domains = own_domains

    def parse(self, raw_email_headers: aioimaplib.Response) -> EmailHeaders:
        """Parse raw email headers when an email is received.

        :param raw_email_headers: the relevant email header data

        """
        message_headers = BytesHeaderParser().parsebytes(raw_email_headers.lines[1])

        parsed_email = EmailHeaders(
            to_address=self._parse_address(message_headers, "To"),
            from_address=self._parse_address(message_headers, "From")[0],
            authentication_results=self._parse_authentication_result(message_headers),
            recieved=self._parse_recieved(message_headers),
            cc_address=self._parse_address(message_headers, "Cc"),
            bcc_address=self._parse_address(message_headers, "Bcc"),
        )
        return parsed_email

    def _parse_address(self, message_headers: Message, index: str) -> list[str]:
        if message_headers[index] is None:
            return [""]

        if index == "From":
            return [re.findall(EMAIL_REGEX, message_headers[index])[0]]
        if index == "To":
            to_addresses = []
            for own_domain in self.own_domains:
                to_addresses += [
                    addres
                    for addres in re.findall(EMAIL_REGEX, message_headers[index])
                    if own_domain == addres.split("@")[1]
                ]
            if to_addresses:
                return to_addresses

            return [""]

        return re.findall(EMAIL_REGEX, message_headers[index])

    @staticmethod
    def _parse_authentication_result(message_headers: Message) -> AuthenticationResult:
        if message_headers["Authentication-Results"] is None:
            return AuthenticationResult(
                **{check: Result("none") for check in SERVER_SIDE_CHECKS}
            )

        checks_result = {}
        for check in SERVER_SIDE_CHECKS:
            match = re.findall(
                rf"{check}=(.*?[\s\W])", message_headers["Authentication-Results"] + " "
            )
            if match:
                checks_result[check] = Result(match[0][:-1])
            else:
                checks_result[check] = Result("none")
        return AuthenticationResult(**checks_result)

    @staticmethod
    def _parse_recieved(message_headers: Message) -> list[Transaction]:
        transaction_path = []
        for (
            entry
        ) in (
            message_headers._headers  # type: ignore[attr-defined] # pylint: disable=protected-access
        ):
            if entry[0] == "Received":
                from_domain = entry[1].split(" ")[1]
                if to_addresses := re.findall(EMAIL_REGEX, entry[1]):
                    to_address = to_addresses[0]
                else:
                    to_address = "unknown"
                try:
                    timestamp = datetime.strptime(
                        entry[1].split(";")[1].split("(")[0].strip(),
                        "%a, %d %b %Y %H:%M:%S %z",
                    )
                except (ValueError, IndexError):
                    timestamp = datetime.utcnow()

                tls = "using TLS" in entry[1].split(";")[0]

                transaction_path.append(
                    Transaction(
                        from_domain=from_domain,
                        to_address=to_address,
                        timestamp=timestamp,
                        tls=tls,
                    )
                )
        return transaction_path
