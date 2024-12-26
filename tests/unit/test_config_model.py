from pydantic import ValidationError

from laelaps.config_model import EncryptionConfigModel, ImapConfigModel, UserConfigModel


def test_user_config_model_valid():
    # Arrange & Act
    config = UserConfigModel(
        own_domains=["example.com", "test.com"],
        target_folder_verified="Verified",
        target_folder_failed_validation="Failed Validation",
    )
    # Assert
    assert config.own_domains == ["example.com", "test.com"]
    assert config.target_folder_verified == "Verified"
    assert config.target_folder_failed_validation == "Failed Validation"


def test_user_config_model_valid_string_domains():
    # Arrange & Act
    config = UserConfigModel(
        own_domains="example.com,test.com",
        target_folder_verified="Verified",
        target_folder_failed_validation="Failed Validation",
    )
    # Assert
    assert config.own_domains == ["example.com", "test.com"]


def test_user_config_model_valid_single_string_domain():
    # Arrange & Act
    config = UserConfigModel(
        own_domains="example.com",
        target_folder_verified="Verified",
        target_folder_failed_validation="Failed Validation",
    )
    # Assert
    assert config.own_domains == ["example.com"]


def test_user_config_model_invalid_missing_fields():
    # Arrange & Act
    try:
        UserConfigModel(own_domains=["example.com", "test.com"])
    except ValidationError as e:
        # Assert
        assert "target_folder_verified" in str(e)
        assert "target_folder_failed_validation" in str(e)


def test_user_config_model_invalid_empty_domains():
    # Arrange & Act
    try:
        UserConfigModel(
            own_domains=[],
            target_folder_verified="Verified",
            target_folder_failed_validation="Failed Validation",
        )
    except ValidationError as e:
        # Assert
        assert "own_domains" in str(e)


def test_imap_config_model_valid():
    # Arrange & Act
    config = ImapConfigModel(
        host="imap.gmail.com", mailbox="INBOX", username="USERNAME", password="PASSWORD"
    )
    # Assert
    assert config.host == "imap.gmail.com"
    assert config.mailbox == "INBOX"
    assert config.username == "USERNAME"
    assert config.password.get_secret_value() == "PASSWORD"


def test_encryption_config_model_valid():
    # Arrange & Act
    config = EncryptionConfigModel(key="KEY")
    # Assert
    assert config.key.get_secret_value() == "KEY"
