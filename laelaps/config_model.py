# SPDX-FileCopyrightText: 2024 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0
"""Defines the configuration model."""
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class ImapConfigModel(BaseModel):
    """Configuration model for the imap server."""

    host: str = Field(
        ..., description="Host of the imap server", examples=["imap.gmail.com"]
    )
    mailbox: str = Field(
        ..., description="Folder that needs to be monitored", examples=["INBOX"]
    )
    username: str = Field(..., description="Username to log in to the imap server")
    password: SecretStr = Field(
        ..., description="Password to log in to the imap server"
    )


class UserConfigModel(BaseModel):
    """Configuration model for the user."""

    own_domains: list[str] | str = Field(
        ...,
        description="List of domains that are owned by the user",
        examples=[["own_domain.com"]],
    )
    target_folder_verified: str = Field(
        ...,
        description="Folder to move email to when validation is successful",
        examples=["Verified"],
    )
    target_folder_failed_validation: str = Field(
        ...,
        description="Folder to move email to when validation is failed",
        examples=["Failed Validation"],
    )

    @field_validator("own_domains", mode="before")
    @classmethod
    def split_own_domains(cls, own_domains):
        """Split own_domains if it is a string."""
        if isinstance(own_domains, str):
            if "," in own_domains:
                return own_domains.split(",")
            return [own_domains]
        return own_domains


class EncryptionConfigModel(BaseModel):
    """Configuration model for encryption."""

    key: SecretStr = Field(..., description="Key to encrypt and decrypt email headers")


class ConfigModel(BaseSettings):
    """Laelaps configuration model."""

    imap: ImapConfigModel
    user: UserConfigModel
    encryption: EncryptionConfigModel

    class Config:
        """Configuration for the configuration model."""

        env_prefix = "LAELAPS_"
        env_nested_delimiter = "__"
