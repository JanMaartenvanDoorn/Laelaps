# SPDX-FileCopyrightText: 2023 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0
"""Defines the main loop."""
import asyncio
import re
import signal
from types import FrameType

import structlog
import toml
from email_validator import EmailNotValidError, caching_resolver, validate_email

from laelaps.alias_generation_and_verification import AliasInformationExtractor
from laelaps.database_repository import DatabaseRepository
from laelaps.email_headers_models import EmailHeaders, Result
from laelaps.email_headers_parser import SERVER_SIDE_CHECKS, EmailHeadersParser
from laelaps.imap_repository import IMAPRepository


class SignalHandler:
    """Simple class to handle termination signals."""

    _keep_monitoring: bool = True

    def __init__(self):
        """Initialize signal handler."""
        self.logger = structlog.getLogger(self.__class__.__name__)
        signal.signal(signal.SIGINT, self._exit_gracefully)
        signal.signal(signal.SIGTERM, self._exit_gracefully)

    def keep_monitoring(self) -> bool:
        """Tell if we need to keep monitoring."""
        return self._keep_monitoring

    def _exit_gracefully(self, signum: int, frame: FrameType) -> None:
        """Exit monitor gracefully."""
        self.logger.info(
            "Exiting gracefully, this may take a while.",
            signum=signum,
            frame_lineno=frame.f_lineno,
        )

        self._keep_monitoring = False


async def idle_loop(
    host: str, user: str, password: str, mailbox: str, config: dict
) -> None:
    """Start the idle loop.

    Handles the actual imap IDLE loop that monitors for new messages on the server.

    :param user: Username to log in to the imap server
    :param password: Password to log in to the imap server
    :param mailbox: Folder that needs to be monitored
    :param host: Host of the imap server
    :param config: Dict that contains user config.

    """
    signal_handler = SignalHandler()

    # Start context manager
    async with IMAPRepository(
        host=host, user=user, password=password, mailbox=mailbox
    ) as imap_repository:
        logger = structlog.getLogger("Imap Monitor")
        logger.info("Monitoring folder.", folder=mailbox)

        # Start loop
        while signal_handler.keep_monitoring():
            # Wait until a new email message is received by the server.
            idle = await imap_repository.wait_for_new_email_message()

            # Get Uids of new messages
            email_uids = await imap_repository.get_uids_new_messages()

            # Handle the new emails, usually this is only one. However in the event that there are multiple new messages we process all of them.
            for uid in email_uids:
                # Get the new email message from the server.
                binary_email_headers = (
                    await imap_repository.get_raw_new_email_headers_from_server(uid)
                )

                # Parse email
                if binary_email_headers:
                    email_headers = EmailHeadersParser(
                        config["user"]["own_domains"]  # type: ignore
                    ).parse(binary_email_headers)

                    # Validate and decide target folder
                    target_folder = decide_target_folder(email_headers, config)

                    # Move email to target folder
                    await imap_repository.move_email_to_folder(uid, target_folder)

            # Wait for idle
            await asyncio.wait_for(idle, 1)


def decide_target_folder(email_headers: EmailHeaders, config: dict) -> str:
    """Validate email message and decide to which folder the message has to be moved.

    :param email_headers: Parsed email headers.
    :param config: Dict that contains user config.
    :return: Target folder on the imap folder.

    """
    logger = structlog.getLogger("Receive email listener")

    validations = {}

    # Validate alias itself
    alias_information_extractor = AliasInformationExtractor(
        config["encryption"]["key"], config["user"]["own_domains"][0]
    )

    alias_verification = alias_information_extractor.extract_and_validate_information(
        email_headers["to_address"][0]
    )
    validations["alias_verification"] = alias_verification[
        "passed_signature_verification"
    ]

    # Validate from address, including DNS MX verification
    try:
        from_address_validation = validate_email(
            email_headers.from_address, dns_resolver=caching_resolver(timeout=10)
        )
        validations["from_address_validation"] = bool(from_address_validation)
    except EmailNotValidError as exception:
        logger.error(
            "From address is not a valid email address.",
            alias=email_headers.from_address,
            exception=exception.__class__.__name__,
        )

        validations["from_address_validation"] = False

    # Check if server-side authentication(DKIM, SPF, DMARC) has passed
    validations.update(
        {
            attribute: email_headers.authentication_results[attribute] == Result.PASSED
            for attribute in SERVER_SIDE_CHECKS
        }
    )

    # Check if email was transferred using TLS
    for transfer in email_headers.received:
        # For now ok if any of the transactions used TLS
        # TODO make this more advanced such that TLS is required for all transactions outside own MTA's
        if transfer.tls:
            validations.update({"tls": True})

    # Validate if alias was registered for sending domain
    # Get relations for this alias (to_address)
    database_repository = DatabaseRepository()
    allowed_domains = database_repository.get_allowed_domains(
        email_headers.to_address[0]
    )

    # Check if domain matches any of the allowed options
    from_domain = email_headers.from_address.split("@")[1]

    allowed_domain_pattern = re.compile(
        r"([a-z0-9]*?\.){0,3}?" + from_domain.replace(".", r"\.")
    )
    validations["send_from_allowed_domain"] = False
    for domain in allowed_domains:
        if allowed_domain_pattern.match(domain):
            validations.update({"send_from_allowed_domain": True})

    if all(list(validations.values())) or validations["send_from_allowed_domain"]:
        logger.info(
            "Validation passed.", **validations, alias=email_headers.to_address[0]
        )
        return config["user"]["target_folder_verified"]

    logger.info("Validation failed.", **validations, alias=email_headers.to_address[0])

    return config["user"]["target_folder_failed_validation"]


def main() -> None:
    """Run the main loop."""
    config = toml.load("./config.toml")
    asyncio.run(idle_loop(**config["imap"], config=config))
