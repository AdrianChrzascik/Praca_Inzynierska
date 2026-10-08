"""Shared, responsive layouts for the WMS screens."""

from math import ceil

from kivy.metrics import dp
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField


BACKGROUND = get_color_from_hex("#111827")
SURFACE = get_color_from_hex("#1D293B")
HEADER = get_color_from_hex("#293A53")
SELECTED = get_color_from_hex("#31577D")
PRIMARY = get_color_from_hex("#2F75C8")
SECONDARY = get_color_from_hex("#40536B")
DANGER = get_color_from_hex("#A84752")

SCREEN_TITLES = {
    "add_tow": "Nowy towar",
    "edit_tow": "Edycja towaru",
    "tow_select": "Towary",
    "tow_pz_wz": "Wybierz towar",
    "menu_WZ": "Dokumenty WZ",
    "menu_PZ": "Dokumenty PZ",
    "menu_dst": "Dostawcy",
    "menu_odb": "Odbiorcy",
    "add_dst": "Nowy dostawca",
    "edit_dst": "Edycja dostawcy",
    "add_odb": "Nowy odbiorca",
    "edit_odb": "Edycja odbiorcy",
    "add_WZ": "Nowy dokument WZ",
    "add_PZ": "Nowy dokument PZ",
    "edit_WZ": "Edycja dokumentu WZ",
    "edit_PZ": "Edycja dokumentu PZ",
    "dst_to_pz": "Wybierz dostawcę",
    "odb_to_wz": "Wybierz odbiorcę",
}

# KivyMD multiplies each declared table width by five when rendering.
COLUMN_WEIGHTS = {
    "Kod": 1.0,
    "Nazwa": 2.5,
    "Ilość": 1.1,
    "Cena": 1.1,
    "Cena netto": 1.2,
    "VAT %": 0.8,
    "Netto": 1.3,
    "VAT": 1.1,
    "Brutto": 1.3,
    "Wartość netto": 1.4,
    "Wartość brutto": 1.4,
    "Numer": 1.0,
    "Wartość": 1.5,
    "Odbiorca": 2.5,
    "Dostawca": 2.5,
    "Nip": 1.7,
}

BUTTON_TEXT = {
    "Zatwierdz towar/Dodaj kolejny towar": "Dodaj pozycję",
    "Potwierdz Edycje": "Zapisz zmiany",
    "Usun Zaznaczone": "Usuń zaznaczone",
    "Usun": "Usuń pozycję",
    "Powrót/anuluj": "Anuluj",
    "Dodaj dostawce": "Dodaj dostawcę",
    "Edytuj dostawce": "Edytuj dostawcę",
    "Dodaj odbiorce": "Dodaj odbiorcę",
    "Edytuj odbiorce": "Edytuj odbiorcę",
    "Zamknij Program": "Zamknij program",
    "Rejestruj": "Zapisz dokument",
    "Wystaw WZ": "Nowy WZ",
    "Wystaw PZ": "Nowy PZ",
}


def create_table(**kwargs):
    """Give table columns useful widths before MDDataTable builds its cells."""
    columns = kwargs["column_data"]
    total_weight = sum(COLUMN_WEIGHTS.get(column[0], 1.0) for column in columns)
    kwargs["column_data"] = [
        (
            column[0],
            max(dp(20), dp(180) * COLUMN_WEIGHTS.get(column[0], 1.0) / total_weight),
            *column[2:],
        )
        for column in columns
    ]
    kwargs.setdefault("background_color_header", HEADER)
    kwargs.setdefault("background_color_cell", SURFACE)
    kwargs.setdefault("background_color_selected_cell", SELECTED)
    return MDDataTable(**kwargs)


def _style_button(button, height=dp(46)):
    button.text = BUTTON_TEXT.get(button.text, button.text)
    button.size_hint = (1, None)
    button.height = height
    button.font_size = "14sp"
    if button.text.startswith(("Usuń", "Zamknij")):
        button.md_bg_color = DANGER
    elif button.text.startswith(("Powrót", "Anuluj")):
        button.md_bg_color = SECONDARY
    else:
        button.md_bg_color = PRIMARY


def _make_header(title, subtitle=None):
    height = dp(72) if subtitle else dp(48)
    header = MDBoxLayout(
        orientation="vertical", size_hint_y=None, height=height, spacing=dp(2)
    )
    header.add_widget(
        MDLabel(
            text=title,
            font_style="H5",
            bold=True,
            size_hint_y=None,
            height=dp(44),
        )
    )
    if subtitle:
        header.add_widget(
            MDLabel(
                text=subtitle,
                font_style="Body2",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(24),
            )
        )
    return header


def _set_grid_columns(grid, count, columns, row_height, gap):
    grid.cols = min(count, columns)
    rows = ceil(count / grid.cols)
    grid.height = row_height * rows + gap * (rows - 1)


def _attach_menu(layout, widgets):
    buttons = [widget for widget in widgets if isinstance(widget, MDRaisedButton)]
    status = next((widget for widget in widgets if isinstance(widget, MDLabel)), None)

    card = MDBoxLayout(
        orientation="vertical",
        size_hint=(0.82, None),
        pos_hint={"center_x": 0.5},
        height=dp(390),
        padding=dp(24),
        spacing=dp(14),
        md_bg_color=SURFACE,
    )
    card.add_widget(_make_header("WMS", "Wybierz obszar pracy"))
    menu = GridLayout(
        cols=2,
        spacing=dp(12),
        row_force_default=True,
        row_default_height=dp(58),
        size_hint_y=None,
        height=dp(198),
    )
    for button in buttons:
        _style_button(button, dp(58))
        menu.add_widget(button)
    card.add_widget(menu)
    if status:
        status.size_hint_y = None
        status.height = dp(24)
        status.theme_text_color = "Secondary"
        card.add_widget(status)

    layout.add_widget(Widget())
    layout.add_widget(card)
    layout.add_widget(Widget())


def attach_screen_layout(screen, layout):
    """Place the existing screen widgets into a readable form/table/action layout."""
    widgets = list(reversed(layout.children))
    layout.clear_widgets()
    layout.padding = [dp(20), dp(16), dp(20), dp(16)]
    layout.spacing = dp(12)
    layout.md_bg_color = BACKGROUND

    if screen.name == "main_menu":
        _attach_menu(layout, widgets)
        screen.add_widget(layout)
        return

    title_widget = next(
        (widget for widget in widgets if isinstance(widget, MDLabel) and widget.text.strip()),
        None,
    )
    title = SCREEN_TITLES.get(
        screen.name, title_widget.text if title_widget else "WMS"
    )
    layout.add_widget(_make_header(title))

    fields = [
        widget
        for widget in widgets
        if isinstance(widget, (MDTextField, MDLabel)) and widget is not title_widget
    ]
    if fields:
        form = GridLayout(
            cols=2,
            spacing=dp(10),
            row_force_default=True,
            row_default_height=dp(62),
            size_hint_y=None,
        )
        for field in fields:
            field.size_hint_x = 1
            if isinstance(field, MDTextField):
                field.mode = "rectangle"
                if field.icon_right == "language-python":
                    field.icon_right = ""
                if field.hint_text == "Nip":
                    field.hint_text = "NIP"
            else:
                field.size_hint_y = None
                field.height = dp(56)
                field.font_style = "Subtitle1"
            form.add_widget(field)
        layout.add_widget(form)

        def resize_form(_layout, width):
            columns = 2 if width >= dp(700) else 1
            _set_grid_columns(form, len(fields), columns, dp(62), dp(10))

        layout.bind(width=resize_form)
        resize_form(layout, layout.width)

    table = next((widget for widget in widgets if isinstance(widget, MDDataTable)), None)
    if table:
        table.size_hint = (1, 1)
        layout.add_widget(table)
    else:
        layout.add_widget(Widget())

    buttons = [widget for widget in widgets if isinstance(widget, MDRaisedButton)]
    if buttons:
        actions = GridLayout(
            cols=2,
            spacing=dp(10),
            row_force_default=True,
            row_default_height=dp(46),
            size_hint_y=None,
        )
        for button in buttons:
            _style_button(button)
            actions.add_widget(button)
        layout.add_widget(actions)

        def resize_actions(_layout, width):
            columns = (4 if len(buttons) == 4 else 3) if width >= dp(1000) else 2
            _set_grid_columns(actions, len(buttons), columns, dp(46), dp(10))

        layout.bind(width=resize_actions)
        resize_actions(layout, layout.width)

    screen.add_widget(layout)
