<!--
SPDX-FileCopyrightText: 2023 Jan Maarten van Doorn <laelaps@vandoorn.cloud>

SPDX-License-Identifier: MPL-2.0
-->

# Laelaps
Laelaps is an IMAP monitoring application that is capable of verifying signed aliases. This is particularly useful when using different catchall-based aliases. Catchall-based aliases are a convenient way to generate unique email addresses for online accounts and reduce the impact of potential data leaks. However with catchall mode turned on there is a risk of attracting lots of spam.

Laelaps solves this problem by verifying whether an alias is indeed generated by the user and not by some other random party such as a spammer. This is achieved without registering the known aliases by using cryptographic signatures within generated aliases themselves. In practice a user generates an alias using a private key and the [TeumessianFox](https://github.com/Marmalade8478/TeumessianFox) browser extension and Lealaps will separate spam from emails that are send to genuine aliases. This way the user can easily generate new aliasses and still be in full controll of messages send to her/his inbox.

As a bonus, albeit rather experimental, Laelaps can perform other checks on incoming email messages by analysing the message headers, these checks include:

- Verfying whether SPF, DMARC and DKIM passed. 
- Posibility to register an aliasses for a specific domain that is allowed to send messages only to this specific alias.
- Check wether the email weas send with TLS enabled
- Check wether the sending email address exists

Laelaps moves incoming messages either to an inbox folder for messages that passed validation or to a folder that failed validation.

## Installation
Run the following in your favorite python environment.

```shell
pip install laelaps
```

## Configuring
Create a `config.toml` with the folowing contents in your working directory:

```toml
[imap]
host = "your.imap.server.host"
user = "yourImapUserName"
password = "ImapPassword"
mailbox = "FolderToMonitor"

[encryption]
# Generate yourself and keep safe!
key = "32CharacterStringEncryptionKey00"

[user]
own_domains = [ "list.of", "catchall.domains"]
target_folder_verified = "FolderToForVerifiedEmails"
target_folder_failed_validation = "FolderToForFailedVerificationEmails"
```

## Running
Start laelaps with:
```shell
python -m laelaps
```
Stop laelaps with
<kbd>ctrl</kbd>+<kbd>C</kbd>

### Running with docker-compose
Start the laelaps container with (make sure there is a ``conf.toml`` in the root of the project):
```shell
docker-compose up
```

## Develop
To install dev/test tools run (in the root directory)
```shell
pip install .[test]
```
Running linting and tests is done by running:
```shell
bash format.sh
```
