"""Pure data-conversion helpers shared by the application and its tests."""

from collections.abc import Iterable, Sequence
from typing import Any


def convert_to_dict(rows: Iterable[Sequence[Any]]) -> list[dict[str, Any]]:
    """Convert product rows ordered as code, name, quantity, and price."""
    return [
        {
            "tow_kod": row[0],
            "tow_name": row[1],
            "ilo_is": row[2],
            "ce": row[3],
        }
        for row in rows
    ]


def convert_to_dict_odb(rows: Iterable[Sequence[Any]]) -> list[dict[str, Any]]:
    """Convert recipient rows ordered as code, name, and tax number."""
    return [
        {"kod_odb": row[0], "name_odb": row[1], "nip": row[2]}
        for row in rows
    ]


def convert_to_dict_dst(rows: Iterable[Sequence[Any]]) -> list[dict[str, Any]]:
    """Convert supplier rows ordered as code, name, and tax number."""
    return [
        {"kod_dst": row[0], "name_dst": row[1], "nip": row[2]}
        for row in rows
    ]


def convert_to_dict_WZ(rows: Iterable[Sequence[Any]]) -> list[dict[str, Any]]:
    """Convert WZ document rows ordered as number, value, and recipient."""
    return [
        {"idwz": row[0], "val": row[1], "name_odb": row[2]}
        for row in rows
    ]


def convert_to_dict_PZ(rows: Iterable[Sequence[Any]]) -> list[dict[str, Any]]:
    """Convert PZ document rows ordered as number, value, and supplier."""
    return [
        {"idpz": row[0], "val": row[1], "name_dst": row[2]}
        for row in rows
    ]


def zamien_przecinek_na_kropke(tekst: str) -> str:
    """Replace decimal commas with dots, leaving other text unchanged."""
    return tekst.replace(",", ".")