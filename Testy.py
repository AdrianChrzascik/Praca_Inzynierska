import importlib.util
import sys
import types
import unittest
from tempfile import TemporaryDirectory
from decimal import Decimal
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch

from konwersje import (
    convert_to_dict,
    convert_to_dict_dst,
    convert_to_dict_odb,
    convert_to_dict_PZ,
    convert_to_dict_WZ,
    zamien_przecinek_na_kropke,
)
from vat import line_totals, totals_from_net, vat_rate
from dates import issue_date_text, parse_issue_date, timestamp_text
from startup_dialog import find_installer
import startup_dialog
from user_settings import load_theme, save_theme


class TestKonwersje(unittest.TestCase):
    def test_product_converter_accepts_tuples_and_lists(self):
        rows = [(1, "Product1", 10, 50.0), [2, "Product2", 20, 30.0]]

        self.assertEqual(
            convert_to_dict(rows),
            [
                {"tow_kod": 1, "tow_name": "Product1", "ilo_is": 10, "ce": 50.0},
                {"tow_kod": 2, "tow_name": "Product2", "ilo_is": 20, "ce": 30.0},
            ],
        )

    def test_entity_converters_use_entity_specific_keys(self):
        self.assertEqual(
            convert_to_dict_odb([(1, "Recipient", "123")]),
            [{"kod_odb": 1, "name_odb": "Recipient", "nip": "123"}],
        )
        self.assertEqual(
            convert_to_dict_dst([(2, "Supplier", "456")]),
            [{"kod_dst": 2, "name_dst": "Supplier", "nip": "456"}],
        )

    def test_document_converters_distinguish_wz_and_pz(self):
        self.assertEqual(
            convert_to_dict_WZ([(3, 100.0, "Recipient")]),
            [{"idwz": 3, "val": 100.0, "name_odb": "Recipient"}],
        )
        self.assertEqual(
            convert_to_dict_PZ([(4, 200.0, "Supplier")]),
            [{"idpz": 4, "val": 200.0, "name_dst": "Supplier"}],
        )

    def test_converters_return_empty_lists_for_empty_rows(self):
        converters = (
            convert_to_dict,
            convert_to_dict_odb,
            convert_to_dict_dst,
            convert_to_dict_WZ,
            convert_to_dict_PZ,
        )
        for converter in converters:
            with self.subTest(converter=converter.__name__):
                self.assertEqual(converter([]), [])

    def test_decimal_separator_conversion(self):
        self.assertEqual(zamien_przecinek_na_kropke("10,5"), "10.5")
        self.assertEqual(zamien_przecinek_na_kropke("20.3"), "20.3")


class TestSchematInstalatora(unittest.TestCase):
    def test_schema_is_non_destructive_and_creates_all_tables_if_missing(self):
        schema_path = Path(__file__).parent / "installer" / "schema.sql"
        schema = schema_path.read_text(encoding="utf-8").upper()

        self.assertNotIn("DROP TABLE", schema)
        for table in ("TOW", "ODB", "DST", "WZ", "WZ_P", "PZ", "PZ_P"):
            with self.subTest(table=table):
                self.assertIn(f"CREATE TABLE IF NOT EXISTS `{table}`", schema)

    def test_vat_columns_exist_on_goods_and_document_lines(self):
        schema = (Path(__file__).parent / "installer" / "schema.sql").read_text(encoding="utf-8")
        self.assertEqual(schema.count("`vat_rate` DECIMAL(5,2) NOT NULL DEFAULT 0"), 3)

    def test_date_columns_keep_legacy_records_without_invented_dates(self):
        schema = (Path(__file__).parent / "installer" / "schema.sql").read_text(encoding="utf-8")
        for column, column_type in (
            ("added_at", "DATETIME"), ("modified_at", "DATETIME"),
            ("issue_date", "DATE"),
        ):
            with self.subTest(column=column):
                self.assertIn(f"`{column}` {column_type} NULL", schema)


class TestVat(unittest.TestCase):
    def test_net_vat_and_gross_are_rounded_per_line(self):
        self.assertEqual(
            line_totals("10,01", "3", "23"),
            (Decimal("30.03"), Decimal("6.91"), Decimal("36.94")),
        )
        self.assertEqual(
            line_totals("0.05", 1, "10"),
            (Decimal("0.05"), Decimal("0.01"), Decimal("0.06")),
        )

    def test_saved_net_value_keeps_original_document_amount(self):
        self.assertEqual(
            totals_from_net("100.00", "23"),
            (Decimal("100.00"), Decimal("23.00"), Decimal("123.00")),
        )

    def test_invalid_rate_is_rejected(self):
        for invalid in ("-1", "101", "23.123", "abc"):
            with self.subTest(rate=invalid), self.assertRaises(ValueError):
                vat_rate(invalid)


class TestDaty(unittest.TestCase):
    def test_document_date_accepts_real_iso_day(self):
        self.assertEqual(parse_issue_date("2024-02-29"), date(2024, 2, 29))
        self.assertEqual(issue_date_text(date(2024, 2, 29)), "2024-02-29")

    def test_document_date_rejects_invalid_or_ambiguous_text(self):
        for invalid in ("", "2023-02-29", "29.02.2024", "2024-2-9"):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                parse_issue_date(invalid)

    def test_unknown_legacy_timestamp_is_displayed_without_guessing(self):
        self.assertEqual(issue_date_text(None), "Brak daty")
        self.assertEqual(timestamp_text(None), "Brak daty")
        self.assertEqual(timestamp_text(datetime(2024, 2, 29, 13, 45)), "2024-02-29 13:45")


class TestUstawieniaIInstalator(unittest.TestCase):
    def test_theme_is_saved_and_loaded_for_the_user(self):
        with TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "WMS" / "settings.ini"
            self.assertEqual(load_theme(path), "Dark")
            save_theme("Light", path)
            self.assertEqual(load_theme(path), "Light")
            save_theme("Dark", path)
            self.assertEqual(load_theme(path), "Dark")

    def test_installer_is_found_only_with_complete_bundle(self):
        with TemporaryDirectory(dir=Path(__file__).parent) as directory:
            package = Path(directory)
            app = package / "WMS"
            installer = package / "installer"
            app.mkdir()
            installer.mkdir()
            (app / "WMS.exe").touch()
            (package / "Zainstaluj-WMS.cmd").touch()
            for name in ("Run-Installer.ps1", "Install-WMS.ps1", "schema.sql"):
                (installer / name).touch()
            with patch.object(startup_dialog.sys, "frozen", True, create=True), \
                 patch.object(startup_dialog.sys, "executable", str(app / "WMS.exe")):
                self.assertEqual(find_installer(), package / "Zainstaluj-WMS.cmd")
                installed_installer = app / "installer"
                installed_installer.mkdir()
                (app / "Zainstaluj-WMS.cmd").touch()
                for name in ("Run-Installer.ps1", "Install-WMS.ps1", "schema.sql"):
                    (installed_installer / name).touch()
                self.assertEqual(find_installer(), app / "Zainstaluj-WMS.cmd")
                (installed_installer / "schema.sql").unlink()
                (installer / "schema.sql").unlink()
                self.assertIsNone(find_installer())


class TestNumeracjaKodow(unittest.TestCase):
    def setUp(self):
        self.database = Mock()
        self.cursor = self.database.cursor.return_value
        fake_connect = types.SimpleNamespace(mydb=self.database)
        module_path = Path(__file__).parent / "Funkcje_Baza.py"
        spec = importlib.util.spec_from_file_location("funkcje_baza_test", module_path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"Connect": fake_connect}):
            spec.loader.exec_module(self.module)

    def test_suggests_next_numeric_code_for_each_entity(self):
        cases = (
            ("tow", Decimal("17"), "18", "REGEXP"),
            ("odb", 42, "43", "kod_odb"),
            ("dst", None, "1", "kod_dst"),
        )
        for entity, highest, expected, query_part in cases:
            with self.subTest(entity=entity):
                self.cursor.fetchone.return_value = (highest,)
                self.assertEqual(self.module.select_next_code(entity), expected)
                self.assertIn(query_part, self.cursor.execute.call_args.args[0])

    def test_manual_codes_are_saved_unchanged(self):
        cases = (
            (self.module.add_tow, ("ABC-123", "Towar", "12.50")),
            (self.module.add_odb, ("42", "Odbiorca", "123")),
            (self.module.add_dst, ("73", "Dostawca", "456")),
        )
        for add, values in cases:
            with self.subTest(add=add.__name__):
                self.cursor.execute.reset_mock()
                self.database.commit.reset_mock()
                self.assertFalse(add(*values))
                self.assertEqual(self.cursor.execute.call_args.args[1][0], values[0])
                self.database.commit.assert_called_once()

    def test_duplicate_code_is_reported_by_database_layer(self):
        for add, values in (
            (self.module.add_tow, ("18", "Towar", "12.50")),
            (self.module.add_odb, ("43", "Odbiorca", "123")),
            (self.module.add_dst, ("74", "Dostawca", "456")),
        ):
            with self.subTest(add=add.__name__):
                self.cursor.execute.side_effect = self.module.pymysql.err.IntegrityError(1062, "Duplicate entry")
                self.database.rollback.reset_mock()
                self.assertTrue(add(*values))
                self.database.rollback.assert_called_once()
                self.cursor.execute.side_effect = None

    def test_wz_uses_database_document_id_and_saves_vat_snapshot(self):
        self.cursor.lastrowid = 7
        self.cursor.fetchone.return_value = (10,)
        line = ("A1", "Towar", Decimal("10.00"), 2, Decimal("20.00"), Decimal("23.00"))

        self.assertEqual(self.module.add_wz([line], "5"), 7)

        calls = self.cursor.execute.call_args_list
        line_insert = next(call for call in calls if "INSERT INTO wz_p" in call.args[0])
        self.assertEqual(line_insert.args[1], (Decimal("20.00"), Decimal("23.00"), "A1", 7, 2))
        header_update = next(call for call in calls if "UPDATE wz SET val" in call.args[0])
        self.assertEqual(header_update.args[1], (Decimal("20.00"), 7))
        stock_update = next(call for call in calls if "UPDATE tow SET ilo_is" in call.args[0])
        self.assertEqual(stock_update.args[1], (8.0, "A1"))
        self.database.commit.assert_called_once()

    def test_document_date_is_saved_and_updated(self):
        self.cursor.lastrowid = 8
        self.cursor.fetchone.return_value = (10,)
        self.cursor.fetchall.return_value = [("A1", 1)]
        line = ("A1", "Towar", Decimal("10.00"), 1, Decimal("10.00"), Decimal("23.00"))

        self.module.add_wz([line], "5", "2024-02-29")
        insert = next(call for call in self.cursor.execute.call_args_list if "INSERT INTO wz (" in call.args[0])
        self.assertEqual(insert.args[1][-1], date(2024, 2, 29))

        self.cursor.execute.reset_mock()
        self.module.edit_wz([line], 8, "5", "2024-03-01")
        update = next(call for call in self.cursor.execute.call_args_list if "UPDATE wz SET val" in call.args[0])
        self.assertIn("issue_date = %s", update.args[0])
        self.assertIn(date(2024, 3, 1), update.args[1])

    def test_product_dates_are_assigned_by_database_on_insert_and_edit(self):
        self.module.add_tow("A1", "Towar", "10.00", "23")
        self.assertIn("added_at) values", self.cursor.execute.call_args.args[0])
        self.assertIn("NOW()", self.cursor.execute.call_args.args[0])

        self.module.tow_edit("Kod: A1", "Nowa nazwa", "10.00", "23")
        self.assertIn("modified_at = NOW()", self.cursor.execute.call_args.args[0])

    def test_edit_rolls_back_if_stock_is_insufficient(self):
        self.cursor.fetchall.return_value = [("A1", 2)]
        self.cursor.fetchone.return_value = (1,)
        line = ("A1", "Towar", Decimal("10.00"), 1, Decimal("10.00"), Decimal("23.00"))

        with self.assertRaises(ValueError):
            self.module.edit_pz([line], 4, "2")

        self.database.rollback.assert_called_once()
        self.database.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
