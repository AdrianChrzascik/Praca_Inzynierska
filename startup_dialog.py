"""A small WMS-styled error window shown before the Kivy app can start."""

import ctypes
import os
import sys
from pathlib import Path

from user_settings import PALETTES, load_theme


def find_installer():
    application_dir = Path(
        sys.executable if getattr(sys, "frozen", False) else __file__
    ).resolve().parent
    for directory in (application_dir, application_dir.parent):
        launcher = directory / "Zainstaluj-WMS.cmd"
        installer = directory / "installer"
        application = any(
            (directory / relative).is_file()
            for relative in ("WMS.exe", "WMS/WMS.exe", "dist/WMS/WMS.exe")
        )
        if (
            launcher.is_file() and application
            and all((installer / name).is_file() for name in (
                "Run-Installer.ps1", "Install-WMS.ps1", "schema.sql"
            ))
        ):
            return launcher
    return None


def _native_fallback(message, launcher):
    if sys.platform != "win32":
        print(message, file=sys.stderr)
        return
    flags = 0x10 | (0x04 if launcher else 0x00)
    text = message + ("\n\nUruchomić instalator WMS?" if launcher else "")
    answer = ctypes.windll.user32.MessageBoxW(  # type: ignore[attr-defined]
        None, text, "WMS — problem z uruchomieniem", flags
    )
    if launcher and answer == 6:
        try:
            os.startfile(str(launcher))  # type: ignore[attr-defined]
        except OSError as error:
            ctypes.windll.user32.MessageBoxW(  # type: ignore[attr-defined]
                None, f"Nie udało się uruchomić instalatora:\n{error}", "WMS", 0x10
            )


def show_startup_error(message, offer_installer=False):
    launcher = find_installer() if offer_installer else None
    if offer_installer and launcher is None:
        message += "\n\nInstalator nie jest dostępny w tym katalogu. Rozpakuj aktualną paczkę WMS."
    if sys.platform != "win32":
        print(message, file=sys.stderr)
        return

    try:
        import tkinter as tk
    except ImportError:
        _native_fallback(message, launcher)
        return

    window = None
    try:
        colors = PALETTES[load_theme()]
        window = tk.Tk()
        window.title("WMS — problem z uruchomieniem")
        window.configure(bg=colors["background"])
        window.geometry("640x385")
        window.minsize(560, 320)

        card = tk.Frame(window, bg=colors["surface"], padx=24, pady=20)
        card.pack(fill="both", expand=True, padx=18, pady=18)
        tk.Label(
            card, text="WMS  •  Problem z uruchomieniem", bg=colors["surface"],
            fg=colors["text"], font=("Segoe UI", 16, "bold"), anchor="w",
        ).pack(fill="x")
        tk.Frame(card, bg=colors["danger"], height=3).pack(fill="x", pady=(12, 14))

        details = tk.Text(
            card, wrap="word", bg=colors["surface"], fg=colors["text"],
            font=("Segoe UI", 10), relief="flat", borderwidth=0,
            highlightthickness=0, height=9,
        )
        details.insert("1.0", message)
        details.configure(state="disabled")
        details.pack(fill="both", expand=True)

        actions = tk.Frame(card, bg=colors["surface"])
        actions.pack(fill="x", pady=(14, 0))

        def start_installer():
            try:
                os.startfile(str(launcher))  # type: ignore[attr-defined]
            except OSError as error:
                details.configure(state="normal")
                details.insert("end", f"\n\nNie udało się uruchomić instalatora: {error}")
                details.configure(state="disabled")
                return
            window.destroy()

        tk.Button(
            actions, text="Zamknij", command=window.destroy,
            bg=colors["secondary"], fg="white", activeforeground="white",
            relief="flat", padx=18, pady=8, cursor="hand2",
        ).pack(side="right")
        if launcher:
            tk.Button(
                actions, text="Uruchom instalator", command=start_installer,
                bg=colors["primary"], fg="white", activeforeground="white",
                relief="flat", padx=18, pady=8, cursor="hand2",
            ).pack(side="right", padx=(0, 10))
        window.mainloop()
    except (RuntimeError, OSError, tk.TclError):
        if window is not None:
            try:
                window.destroy()
            except tk.TclError:
                pass
        _native_fallback(message, launcher)
