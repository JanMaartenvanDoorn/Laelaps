# SPDX-FileCopyrightText: 2022 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0

import os
import unittest
from pathlib import Path

from laelaps.database_repository import DatabaseRepository

TEST_DATABASE_PATH = Path("test_db.db")


class TestDatabaseRepository(unittest.TestCase):
    def setUp(self) -> None:
        """Setup test database."""
        self.database_repository = DatabaseRepository(TEST_DATABASE_PATH)
        self.database_repository.initialize_database()
        return super().setUp()

    def tearDown(self) -> None:
        """Remove database file."""
        os.remove(TEST_DATABASE_PATH)
        return super().tearDown()

    def test_register_and_get_allowed_domains(self):
        # Arange
        self.database_repository.register_allowed_domains(
            "alias@test.com", "testdomain.com"
        )

        # Act
        allowed_domains = self.database_repository.get_allowed_domains("alias@test.com")

        # Assert
        self.assertEqual(allowed_domains, ["testdomain.com"])
