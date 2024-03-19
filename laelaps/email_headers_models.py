# SPDX-FileCopyrightText: 2024 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0
"""Defines internal data models."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Result(Enum):
    """Enum of possible outcomes of server side checks.

    :param Enum: Build-in python Enum class.

    """

    PASSED = "pass"
    FAILED = "fail"
    UNKNOWM = "none"
    SOFTFAIL = "softfail"
    NEUTRAL = "neutral"
    TEMPERROR = "temperror"
    PERMERROR = "permerror"
    BESTGUESSPASS = "bestguesspass"


class AuthenticationResult(BaseModel):
    """Describes the Authentication result.

    Note that this does not contain all the information that is available in the authentication headers and a selection
    of interesting information is made.

    :param BaseModel: Pydantic base model

    """

    dkim: Result
    spf: Result
    dmarc: Result

    def __getitem__(self, item):
        """Get item via a key-value index."""
        return getattr(self, item)


class Transaction(BaseModel):
    """Describes a receive transaction.

    A chain or list of these transactions makes it possible to trace the path of the email before it was delivered.

    :param BaseModel: Pydantic base model

    """

    from_domain: str
    to_address: str
    timestamp: datetime
    tls: bool

    def __getitem__(self, item):
        """Get item via a key-value index."""
        return getattr(self, item)


class EmailHeaders(BaseModel):
    """Describes the internal model for the email headers.

    Note that this does not contain all the information that is available in the headers. A selection of interesting
    information is made.

    :param BaseModel: Pydantic base model

    """

    to_address: str | list[str]
    from_address: str
    authentication_results: AuthenticationResult
    received: list[Transaction]
    cc_address: str | list[str]
    bcc_address: str | list[str]

    def __getitem__(self, item):
        """Get item via a key-value index."""
        return getattr(self, item)
