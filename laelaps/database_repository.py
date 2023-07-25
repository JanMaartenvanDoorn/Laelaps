# SPDX-FileCopyrightText: 2023 Jan Maarten van Doorn <laelaps@vandoorn.cloud>
#
# SPDX-License-Identifier: MPL-2.0
"""Defines database repository."""
import sqlite3
from pathlib import Path

DEFAULT_DATABASE_PATH = Path("local_test.db")


class DatabaseRepository:
    """Repository that give access to all information stored in the database."""

    def __init__(self, database_filepath: Path = DEFAULT_DATABASE_PATH) -> None:
        """Initialize database repository."""
        self.connection = sqlite3.connect(database_filepath)
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize database if not already done."""
        cur = self.connection.cursor()
        query = """CREATE TABLE IF NOT EXISTS "alias_domain" (
                    "alias"	TEXT,
                    "domain"	TEXT UNIQUE,
                    PRIMARY KEY("domain"),
                    UNIQUE("domain")
                );"""
        cur.execute(query)

    def get_allowed_domains(self, alias: str) -> list[str]:
        """Get allowed domains for a specific alias."""
        cur = self.connection.cursor()
        query = """SELECT domain FROM alias_domain WHERE alias= :alias"""
        allowed_domains = cur.execute(query, {"alias": str(alias)}).fetchall()
        return [domain[0] for domain in allowed_domains]

    def register_allowed_domains(self, alias: str, domain: str):
        """Register an alias - domain relation."""
        cursor = self.connection.cursor()
        data = {"alias": alias, "domain": domain}
        query = """INSERT INTO alias_domain VALUES ( :alias, :domain)"""
        cursor.execute(query, data)
        self.connection.commit()
