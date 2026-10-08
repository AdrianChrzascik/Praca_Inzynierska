"""MariaDB connection configuration for both source runs and PyInstaller builds."""

from __future__ import annotations

import configparser
import os
import sys
from pathlib import Path

import pymysql
from startup_dialog import show_startup_error


def _config_path() -> Path:
    configured_path = os.environ.get("WMS_CONFIG_PATH")
    if configured_path:
        return Path(configured_path).expanduser()

    program_data = os.environ.get("PROGRAMDATA")
    if program_data:
        installed_config = Path(program_data) / "WMS" / "database.ini"
        if installed_config.is_file():
            return installed_config

    executable_dir = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
    return executable_dir / "database.ini"


def _show_startup_error(message: str, offer_installer=False) -> None:
    show_startup_error(message, offer_installer=offer_installer)


def _connect() -> pymysql.connections.Connection:
    config_path = _config_path()
    parser = configparser.ConfigParser()

    if not config_path.is_file():
        _show_startup_error(
            "Nie znaleziono konfiguracji bazy danych.\n\n"
            f"Oczekiwany plik: {config_path}\n"
            "Uruchom instalator WMS albo utwórz plik database.ini.",
            offer_installer=True,
        )
        raise SystemExit(1)

    try:
        parser.read(config_path, encoding="utf-8-sig")
        database = parser["database"]
        connection = pymysql.connect(
            host=database.get("host", "127.0.0.1"),
            port=database.getint("port", 3306),
            user=database["user"],
            password=database["password"],
            database=database.get("name", "mydb"),
            charset="utf8mb4",
            connect_timeout=8,
        )
        cursor = connection.cursor()
        cursor.execute(
            "SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN ('tow', 'wz_p', 'pz_p', 'wz', 'pz') "
            "AND COLUMN_NAME IN ('vat_rate', 'added_at', 'modified_at', 'issue_date')"
        )
        available = {tuple(row) for row in cursor.fetchall()}
        required = {
            ("tow", "vat_rate"), ("wz_p", "vat_rate"), ("pz_p", "vat_rate"),
            ("tow", "added_at"), ("tow", "modified_at"),
            ("wz", "issue_date"), ("pz", "issue_date"),
        }
        missing = required - available
        if missing:
            connection.close()
            _show_startup_error(
                "Baza danych wymaga aktualizacji dla obsługi VAT i dat.\n\n"
                "Uruchom ponownie Zainstaluj-WMS.cmd, aby dodać brakujące kolumny "
                "bez usuwania danych.",
                offer_installer=True,
            )
            raise SystemExit(1)
        return connection
    except (KeyError, configparser.Error, OSError, pymysql.MySQLError) as error:
        _show_startup_error(
            "Nie można połączyć się z MariaDB.\n\n"
            f"Konfiguracja: {config_path}\n"
            "Sprawdź, czy usługa MariaDB działa oraz czy dane w database.ini są poprawne.\n\n"
            f"Szczegóły: {error}",
            offer_installer=True,
        )
        raise SystemExit(1) from error


mydb = _connect()
cur = mydb.cursor()
