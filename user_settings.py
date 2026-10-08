"""Small user preferences shared by the GUI and startup error window."""

import configparser
import os
from pathlib import Path


PALETTES = {
    "Dark": {
        "background": "#111827", "surface": "#1D293B", "header": "#293A53",
        "selected": "#31577D", "primary": "#2F75C8", "secondary": "#40536B",
        "danger": "#A84752", "text": "#F5F7FB", "muted": "#BBC7D8",
    },
    "Light": {
        "background": "#F3F6FB", "surface": "#FFFFFF", "header": "#DFEAF7",
        "selected": "#D4E8FF", "primary": "#2F75C8", "secondary": "#61758E",
        "danger": "#B54752", "text": "#1D2939", "muted": "#526277",
    },
}


def settings_path():
    app_data = os.environ.get("APPDATA")
    base = Path(app_data) if app_data else Path.home() / ".config"
    return base / "WMS" / "settings.ini"


def load_theme(path=None):
    config = configparser.ConfigParser()
    try:
        config.read(path or settings_path(), encoding="utf-8")
        style = config.get("appearance", "theme", fallback="Dark")
    except (configparser.Error, OSError):
        return "Dark"
    return style if style in PALETTES else "Dark"


def save_theme(style, path=None):
    if style not in PALETTES:
        raise ValueError("Nieznany motyw WMS.")
    destination = Path(path or settings_path())
    destination.parent.mkdir(parents=True, exist_ok=True)
    config = configparser.ConfigParser()
    config["appearance"] = {"theme": style}
    temporary = destination.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        config.write(output)
    temporary.replace(destination)
