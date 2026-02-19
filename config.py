"""
Database configuration for PVIS (pro_intel_2).
Defaults are provided for local development only.
"""

import os


def get_database_url() -> str:
    """Return SQLAlchemy connection string from env or local default."""
    return os.getenv(
        "PVIS_DATABASE_URL",
        "mysql+pymysql://root:Maconoelle86@localhost:3306/pro_intel_2",
    )


def get_mysql_params() -> dict:
    """Return PyMySQL connection params from env or local defaults."""
    return {
        "host": os.getenv("PVIS_DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("PVIS_DB_PORT", "3306")),
        "user": os.getenv("PVIS_DB_USER", "root"),
        "password": os.getenv("PVIS_DB_PASSWORD", "Maconoelle86"),
        "database": os.getenv("PVIS_DB_NAME", "pro_intel_2"),
    }


DATABASE_URL = get_database_url()
