import pymysql
import re
from decimal import Decimal
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from Connect import mydb
from Funkcje_Baza import (
    add_dst,
    add_odb,
    add_pz,
    add_tow,
    add_wz,
    delete_dst,
    delete_odb,
    delete_PZ,
    delete_tow,
    delete_WZ,
    del_pz_p,
    del_wz_p,
    dst_edit,
    edit_pz,
    edit_wz,
    ilo_check,
    odb_edit,
    select_dst2,
    select_dst_where,
    select_odb2,
    select_odb_where,
    select_PZ2,
    select_pz_edit,
    select_next_code,
    select_tow2,
    select_tow_where,
    select_WZ2,
    select_wz_edit,
    tow_edit,
)
from konwersje import zamien_przecinek_na_kropke
from dates import issue_date_text, parse_issue_date, timestamp_text, today_text
from vat import line_totals, money_text, net_price, quantity, totals_from_net, vat_rate
from kivy.metrics import dp
from gui_layout import apply_palette, attach_screen_layout, create_table, set_palette
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog as BaseMDDialog
from kivymd.uix.label import MDLabel
from kivy.utils import get_color_from_hex
from user_settings import PALETTES, load_theme, save_theme


class MDDialog(BaseMDDialog):
    """Use the active WMS palette for all existing application messages."""

    def __init__(self, **kwargs):
        app = App.get_running_app()
        style = app.theme_cls.theme_style if app else load_theme()
        colors = PALETTES[style]
        kwargs.setdefault("title", "WMS")
        kwargs.setdefault("md_bg_color", get_color_from_hex(colors["surface"]))
        kwargs.setdefault("radius", [dp(14)] * 4)
        for button in kwargs.get("buttons", []):
            button.theme_text_color = "Custom"
            button.text_color = get_color_from_hex(colors["primary"])
        super().__init__(**kwargs)


class PartnerSelectField(MDTextField):
    """Open the partner list when the field's right icon is clicked."""

    def __init__(self, select_partner, **kwargs):
        super().__init__(icon_right="account-search", **kwargs)
        self.select_partner = select_partner

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.x >= self.right - dp(48):
            self.select_partner(self)
            return True
        return super().on_touch_down(touch)


def make_document_line(code, name, price, amount, rate):
    if not code.strip() or not name.strip():
        raise ValueError("Wybierz towar i podaj jego nazwę.")
    price = net_price(price)
    amount = quantity(amount)
    rate = vat_rate(rate)
    net, _tax, _gross = line_totals(price, amount, rate)
    return (code.strip(), name.strip(), price, amount, net, rate)


def document_table_row(line):
    code, name, price, amount, saved_net, rate = line
    net, tax, gross = totals_from_net(saved_net, rate)
    return (
        str(code), str(name), money_text(price), str(amount),
        str(rate), money_text(net), money_text(tax), money_text(gross),
    )


def document_totals_text(lines):
    net = tax = gross = Decimal("0.00")
    for line in lines:
        line_net, line_tax, line_gross = totals_from_net(line[4], line[5])
        net += line_net
        tax += line_tax
        gross += line_gross
    return f"Netto: {money_text(net)}  |  VAT: {money_text(tax)}  |  Brutto: {money_text(gross)}"


class DocumentLinesMixin:
    def refresh_lines(self):
        self.table.row_data = [document_table_row(line) for line in self.lines]
        self.total_label.text = document_totals_text(self.lines)

    def add_line_from_fields(self):
        line = make_document_line(
            self.kod.text, self.nazwa.text, self.cena.text,
            self.ilosc.text, self.vat.text,
        )
        if select_tow_where(line[0]) is False:
            raise ValueError("Taki towar nie występuje w bazie.")
        self.lines.append(line)
        self.refresh_lines()
        self.kod.text = self.nazwa.text = self.cena.text = self.ilosc.text = ""
        self.vat.text = "0"

    def delete_selected_lines(self):
        selected = [tuple(row) for row in self.t2]
        remaining = []
        for line in self.lines:
            row = document_table_row(line)
            if row in selected:
                selected.remove(row)
            else:
                remaining.append(line)
        self.lines = remaining
        self.t = []
        self.t2 = []
        self.refresh_lines()


class SuggestedCodeScreen(Screen):
    code_entity = None

    def on_pre_enter(self, *args):
        if not self.text1.text or self.text1.text == getattr(self, "_suggested_code", None):
            self._suggested_code = select_next_code(self.code_entity)
            self.text1.text = self._suggested_code

    def code_error(self):
        code = self.text1.text.strip()
        if self.code_entity == "tow":
            if not code:
                return "Podaj kod towaru."
            if len(code) > 45:
                return "Kod towaru może mieć maksymalnie 45 znaków."
        else:
            if not re.fullmatch(r"[+-]?[0-9]+", code):
                return "Kod musi być liczbą całkowitą."
            try:
                number = int(code)
            except ValueError:
                return "Kod musi mieścić się w zakresie liczby całkowitej bazy danych."
            if number < -2147483648 or number > 2147483647:
                return "Kod musi mieścić się w zakresie liczby całkowitej bazy danych."
        return None

    def refresh_suggestion_after_duplicate(self, code):
        if code == getattr(self, "_suggested_code", None):
            self._suggested_code = select_next_code(self.code_entity)
            self.text1.text = self._suggested_code

    def clear_form(self):
        self.text1.text = ""
        self.text2.text = ""
        self.text3.text = ""
        self._suggested_code = None


class MainMenu(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        button1 = MDRaisedButton(text='Towary')
        button1.bind(on_press=self.tow_menu)

        button2 = MDRaisedButton(text='WZ')
        button2.bind(on_press=self.WZ_menu)

        button3 = MDRaisedButton(text='PZ')
        button3.bind(on_press=self.PZ_menu)

        button4 = MDRaisedButton(text='Dostawcy')
        button4.bind(on_press=self.Dst_menu)

        button5 = MDRaisedButton(text='Odbiorcy')
        button5.bind(on_press=self.Odb_menu)

        button6 = MDRaisedButton(text='Zamknij Program')
        button6.bind(on_press=self.close_program)

        self.theme_button = MDRaisedButton(text='Tryb dzienny')
        self.theme_button.bind(on_press=self.toggle_theme)

        layout.add_widget(button1)
        layout.add_widget(button2)
        layout.add_widget(button3)
        layout.add_widget(button4)
        layout.add_widget(button5)
        layout.add_widget(self.theme_button)
        layout.add_widget(button6)
        self.message_label = MDLabel(text='', size = (50,50))
        layout.add_widget(self.message_label)
        attach_screen_layout(self, layout)

    def tow_menu(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.current = 'tow_select'


    def WZ_menu(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.current = 'menu_WZ'

    def PZ_menu(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.current = 'menu_PZ'

    def Dst_menu(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.current = 'menu_dst'

    def Odb_menu(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.current = 'menu_odb'

    def close_program(self, instance):
        self.message_label.text = 'Zamknij Program'
        App.get_running_app().stop()

    def toggle_theme(self, instance):
        self.app.toggle_theme()

class EditScreenTow(Screen):

    def __init__(self, **kwargs ):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        #self.menu_tow = menu_tow

        okno = MDLabel(text='Edycja Towaru')
        self.kod = MDLabel(text='', size = (5,5))
        self.nazwa = MDTextField(hint_text='Nazwa', text='')
        self.cena = MDTextField(hint_text='Cena netto', text='')
        self.vat = MDTextField(hint_text='VAT %', text='0')
        self.added_at = MDTextField(hint_text='Data dodania', readonly=True)
        self.modified_at = MDTextField(hint_text='Ostatnia edycja', readonly=True)

        layout.add_widget(okno)
        layout.add_widget(self.kod)
        layout.add_widget(self.nazwa)
        layout.add_widget(self.cena)
        layout.add_widget(self.vat)
        layout.add_widget(self.added_at)
        layout.add_widget(self.modified_at)

        button1 = MDRaisedButton(text='Potwierdz Edycje')
        button1.bind(on_press=self.tow_edit)
        layout.add_widget(button1)

        back_button = MDRaisedButton(text="Powrót/anuluj", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def tow_edit(self, instance):
        tow_kod = self.kod.text
        nazwa = self.nazwa.text
        try:
            ce = net_price(self.cena.text)
            rate = vat_rate(self.vat.text)
        except ValueError as error:
            self.show_alert_dialog(instance, str(error), '', '')
            return
        tow_edit(tow_kod, nazwa, ce, rate)
        self.menu_tow.refresh_table()
        self.show_alert_dialog(instance, 'Towar ', tow_kod, ' został zmodyfikowany')
        self.kod.text = ''
        self.nazwa.text = ''
        self.cena.text = ''
        self.vat.text = '0'
        self.go_back(instance)
        self.menu_tow.t2 = []

    def show_alert_dialog(self, instance, text, towar, text2):
        self.dialog = MDDialog(
            text=text + towar + text2,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)
    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = 'tow_select'

class AddScreenTow(SuggestedCodeScreen):
    code_entity = "tow"

    def __init__(self,menu_tow, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        self.menu_tow = menu_tow

        okno = MDLabel(text='Dodanie Towaru')
        self.text1 = MDTextField(hint_text='Kod (można zmienić)')
        self.text2 = MDTextField(hint_text='Nazwa')
        self.text3 = MDTextField(hint_text='Cena netto')
        self.vat = MDTextField(hint_text='VAT %', text='0')
        self.date_info = MDLabel(text='Data dodania zapisze się automatycznie.')

        layout.add_widget(okno)
        layout.add_widget(self.text1)
        layout.add_widget(self.text2)
        layout.add_widget(self.text3)
        layout.add_widget(self.vat)
        layout.add_widget(self.date_info)

        button1 = MDRaisedButton(text='Dodaj')
        button1.bind(on_press=self.tow_add)
        layout.add_widget(button1)

        back_button = MDRaisedButton(text="Powrót/anuluj", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def tow_add(self, instance):
        error = self.code_error()
        if error:
            self.show_alert_dialog(instance, error)
            return

        tow_kod = self.text1.text.strip()
        nazwa = self.text2.text
        try:
            ce = net_price(self.text3.text)
            rate = vat_rate(self.vat.text)
        except ValueError as error:
            self.show_alert_dialog(instance, str(error))
            return
        x = add_tow(tow_kod, nazwa, ce, rate)
        if x is True:
            self.refresh_suggestion_after_duplicate(tow_kod)
            self.show_alert_dialog(instance, 'Towar o tym kodzie już istnieje w bazie.')
        else:
            self.menu_tow.refresh_table()
            self.show_alert_dialog(instance, 'Towar został dodany do bazy.')
            self.go_back(instance)
    def show_alert_dialog(self, instance,text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)

    def go_back(self, instance):
        self.clear_form()
        self.vat.text = '0'
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = 'tow_select'

class TowSelectScreen(Screen):
    t = []
    t2 = []
    kod = ''
    cena = ''
    nazwa = ''
    dane_edit = None
    def __init__(self,dane_edit, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.dane_edit = dane_edit

        # Dodaj layout do umieszczenia danych
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        # Wyświetl dane z tabeli

        self.table = create_table(
            use_pagination=True,
            check=True,
            rows_num=25,
            column_data=[
                ("Kod", dp(30)),
                ("Nazwa", dp(30)),
                ("Ilość", dp(30)),
                ("Cena netto", dp(30)),
                ("VAT %", dp(30)),
                ("Dodano", dp(30)),
                ("Ostatnia edycja", dp(30))
            ],
        )
        self.dane_tow = select_tow2()

        for d in self.dane_tow:
            k, n, i, c, rate, added, modified = d
            self.table.add_row((
                str(k), str(n), str(i), str(c), str(rate),
                timestamp_text(added), timestamp_text(modified),
            ))
        layout.add_widget(self.table)

        # Bind tabel
        self.table.bind(on_check_press=self.checked)
        self.table.bind(on_check_press=self.checked2)

        # Przycisk usuń
        del_button = MDRaisedButton(text="Usun Zaznaczone", height=1)
        del_button.bind(on_press=self.delete)
        layout.add_widget(del_button)

        # Przycisk dodaj
        add_button = MDRaisedButton(text="Dodaj towar", height=1)
        add_button.bind(on_press=self.add)
        layout.add_widget(add_button)

        # Przycisk edytuj
        edit_button = MDRaisedButton(text="Edytuj towar", height=1)
        edit_button.bind(on_press=self.edit)
        layout.add_widget(edit_button)

        # Dodaj przycisk powrotu
        back_button = MDRaisedButton(text="Powrót", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def refresh_table(self):
        self.dane_tow = select_tow2()
        self.table.row_data = [
            tuple(str(value) for value in row[:5])
            + (timestamp_text(row[5]), timestamp_text(row[6]))
            for row in self.dane_tow
        ]

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = 'main_menu'

    def delete(self, instance):
        if len(self.t) == 0:
            self.show_alert_dialog(instance, 'Towar nie został wybrany')
        else:
            for i in self.t:
                try:
                    delete_tow(i)
                except pymysql.err.IntegrityError as e:
                    if e.args[0] == 1451:
                        self.show_alert_dialog(instance, 'Ten towar jest na dokumencie')
                    else:
                        raise


        self.refresh_table()
        self.t = []


    def add(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.current = 'add_tow'

    def edit(self, instance):
        selected = None
        if len(self.t) == 1:
            selected = next((row for row in self.table.row_data if row[0] == self.t[0]), None)
        if selected is None:
            self.show_alert_dialog(instance, 'Towar nie został wybrany')
        else:
            self.manager.transition = SlideTransition(direction='left', duration=0.50)
            self.manager.current = 'edit_tow'
            self.dane_edit.kod.text = 'Kod: ' + selected[0]
            self.dane_edit.nazwa.text = selected[1]
            self.dane_edit.cena.text = selected[3]
            self.dane_edit.vat.text = selected[4]
            self.dane_edit.added_at.text = selected[5]
            self.dane_edit.modified_at.text = selected[6]

    def show_alert_dialog(self, instance,text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)


    def checked(self, instance_table, current_row):
        found = False
        for item in self.t:
            if item == current_row[0]:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t.remove(current_row[0])
        else:
            # Do something else when no matching element is found
            self.t.append(current_row[0])

    def checked2(self, instance_table, current_row):
        found = False
        for item in self.t2:
            if item == current_row:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t2.remove(current_row)
        else:
            # Do something else when no matching element is found
            self.t2.append(current_row)


class TowSelectScreenToPZ(Screen):
    t = []
    t2 = []
    kod = ''
    cena = ''
    nazwa = ''
    dane_edit = None
    dst = ''
    def __init__(self, add_pz, add_wz, edit_pz, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.add_pz = add_pz
        self.add_wz = add_wz
        self.edit_pz = edit_pz
        self.target = add_pz

        # Dodaj layout do umieszczenia danych
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        # Wyświetl dane z tabeli
        self.table = create_table(
            use_pagination=True,
            rows_num=25,
            column_data=[
                ("Kod", dp(30)),
                ("Nazwa", dp(30)),
                ("Ilość", dp(30)),
                ("Cena netto", dp(30)),
                ("VAT %", dp(30))
            ],
        )
        self.refresh_table()
        layout.add_widget(self.table)

        # Bind tabel
        self.table.bind(on_row_press=self.do_doc)



        # Dodaj przycisk powrotu
        back_button = MDRaisedButton(text="Powrót", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def refresh_table(self):
        self.dane_tow = select_tow2()
        self.table.row_data = [tuple(str(value) for value in row[:5]) for row in self.dane_tow]

    def on_pre_enter(self, *args):
        self.refresh_table()

    def do_doc(self, instance_table, instance_row):
        row_num = int(instance_row.index / len(instance_table.column_data))
        row_data = instance_table.row_data[row_num]
        self.target.kod.text = row_data[0]
        self.target.nazwa.text = row_data[1]
        self.target.cena.text = row_data[3]
        self.target.vat.text = row_data[4]
        self.go_back(instance_table)



    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = self.target.name


    def show_alert_dialog(self, instance,text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)

class WZScreen(Screen):
    t = []
    t2 = []
    text1 = ''
    text2 = ''
    text3 = ''
    dane_WZ = []
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'

        # Dodaj layout do umieszczenia danych
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        # Wyświetl dane z tabeli

        self.table = create_table(
            use_pagination=True,
            check=True,
            rows_num=25,
            column_data=[
                ("Numer", dp(30)),
                ("Data wystawienia", dp(30)),
                ("Wartość netto", dp(30)),
                ("VAT", dp(30)),
                ("Wartość brutto", dp(30)),
                ("Odbiorca", dp(30))
            ],
        )
        self.refresh_table()
        layout.add_widget(self.table)

        # Bind tabel
        self.table.bind(on_check_press=self.checked)
        self.table.bind(on_check_press=self.checked2)

        # Przycisk usuń
        del_button = MDRaisedButton(text="Usun Zaznaczone", height=1)
        del_button.bind(on_press=self.delete)
        layout.add_widget(del_button)

        # Przycisk dodaj
        add_button = MDRaisedButton(text="Wystaw WZ", height=1)
        add_button.bind(on_press=self.add)
        layout.add_widget(add_button)

        # Przycisk edytuj
        edit_button = MDRaisedButton(text="Edytuj WZ", height=1)
        edit_button.bind(on_press=self.edit)
        layout.add_widget(edit_button)

        # Dodaj przycisk powrotu
        back_button = MDRaisedButton(text="Powrót", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def refresh_table(self):
        self.dane_WZ = select_WZ2()
        self.table.row_data = [
            (str(number), issue_date_text(document_date), money_text(net),
             money_text(vat), money_text(gross), str(recipient))
            for number, document_date, net, vat, gross, recipient in self.dane_WZ
        ]

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = 'main_menu'

    def delete(self, instance):
        if len(self.t) == 0:
            self.show_alert_dialog2(instance, 'WZ nie został wybrany')
        else:
            for i in self.t:
                delete_WZ(i)
            self.show_alert_dialog2(instance, 'WZ została usunięta.')
            self.refresh_table()
            self.t = []


    def show_alert_dialog(self, instance, text, towar, text2):
        self.dialog = MDDialog(
            text=text + towar + text2,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def show_alert_dialog2(self, instance, text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)

    def add(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.get_screen('add_WZ').issue_date.text = today_text()
        self.manager.current = 'add_WZ'

    def edit(self, instance):
        if len(self.t) != 1:
            self.show_alert_dialog2(instance, 'Wybierz jeden dokument WZ.')
            return
        document_id = int(self.t[0])
        header, lines = select_wz_edit(document_id)
        if not header:
            self.show_alert_dialog2(instance, 'Dokument WZ nie istnieje.')
            return
        self.edit_wz.load_document(document_id, str(header[0][0]), header[0][1], lines)
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.current = 'edit_WZ'


    def checked(self, instance_table, current_row):
        found = False
        for item in self.t:
            if item == current_row[0]:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t.remove(current_row[0])
        else:
            # Do something else when no matching element is found
            self.t.append(current_row[0])

    def checked2(self, instance_table, current_row):
        found = False
        for item in self.t2:
            if item == current_row:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t2.remove(current_row)
        else:
            # Do something else when no matching element is found
            self.t2.append(current_row)

class AddScreenWZ(DocumentLinesMixin, Screen):
    t = []
    t2 = []
    text1 = ''
    text2 = ''
    text3 = ''
    towar_wz = []
    towar_wz_all = []
    odb_wz = ''
    is_wz = 0

    def __init__(self, dane_tow, dane_wz, **kwargs):
        super().__init__(**kwargs)
        self.lines = []
        self.orientation = 'vertical'
        self.dane_tow = dane_tow
        self.dane_wz = dane_wz
        # Dodaj layout do umieszczenia danych
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        self.odb = PartnerSelectField(self.to_dst, hint_text='Odbiorca (wybierz z listy)')
        self.issue_date = MDTextField(hint_text='Data wystawienia (RRRR-MM-DD)', text=today_text())
        self.kod = MDTextField(hint_text='Kod', icon_right = 'language-python')
        self.nazwa = MDTextField(hint_text='Nazwa')
        self.cena = MDTextField(hint_text='Cena netto')
        self.vat = MDTextField(hint_text='VAT %', text='0')
        self.ilosc = MDTextField(hint_text='Ilość')

        layout.add_widget(self.odb)
        layout.add_widget(self.issue_date)
        layout.add_widget(self.kod)
        layout.add_widget(self.nazwa)
        layout.add_widget(self.cena)
        layout.add_widget(self.vat)
        layout.add_widget(self.ilosc)

        self.table = create_table(
            use_pagination=True,
            check=True,
            rows_num=25,
            column_data=[
                ("Kod", dp(30)),
                ("Nazwa", dp(30)),
                ("Cena netto", dp(30)),
                ("Ilość", dp(30)),
                ("VAT %", dp(30)),
                ("Netto", dp(30)),
                ("VAT", dp(30)),
                ("Brutto", dp(30)),
            ],
        )
        layout.add_widget(self.table)
        self.total_label = MDLabel(text=document_totals_text(self.lines))
        layout.add_widget(self.total_label)

        # Przycisk dodaj
        add_button = MDRaisedButton(text="Rejestruj", height=1)
        add_button.bind(on_press=self.add)
        layout.add_widget(add_button)

        # Przycisk nastepny towar
        edit_button = MDRaisedButton(text="Zatwierdz towar/Dodaj kolejny towar", height=1)
        edit_button.bind(on_press=self.save)
        layout.add_widget(edit_button)

        # Przycisk usun
        edit_button = MDRaisedButton(text="Usun", height=1)
        edit_button.bind(on_press=self.delete)
        layout.add_widget(edit_button)

        # Dodaj przycisk Tow
        tow_button = MDRaisedButton(text="Towary", height=1)
        tow_button.bind(on_press=self.to_tow)
        layout.add_widget(tow_button)

        # Dodaj przycisk powrotu
        back_button = MDRaisedButton(text="Powrót", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

        self.table.bind(on_check_press=self.checked)
        self.table.bind(on_check_press=self.checked2)

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = 'menu_WZ'

    def show_alert_dialog(self, instance, text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)

    def delete(self, instance):
        self.delete_selected_lines()

    def add(self, instance):
        if not self.lines:
            self.show_alert_dialog(instance, 'Nie można wystawić WZ bez pozycji.')
            return
        if select_odb_where(self.odb.text.strip()) is False:
            self.show_alert_dialog(instance, 'Wybierz odbiorcę z bazy.')
            return
        try:
            document_date = parse_issue_date(self.issue_date.text)
            add_wz(self.lines, self.odb.text.strip(), document_date)
        except (ValueError, pymysql.MySQLError) as error:
            self.show_alert_dialog(instance, str(error))
            return
        self.lines = []
        self.refresh_lines()
        self.dane_wz.refresh_table()
        self.show_alert_dialog(instance, 'WZ zostało wystawione.')
        self.odb.text = ''
        self.issue_date.text = today_text()
        self.go_back(instance)


    def to_dst(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.get_screen('odb_to_wz').target = self
        self.manager.current = 'odb_to_wz'
    def to_tow(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.get_screen('tow_pz_wz').target = self
        self.manager.current = 'tow_pz_wz'

    def save(self, instance):
        if select_odb_where(self.odb.text.strip()) is False:
            self.show_alert_dialog(instance, 'Wybierz odbiorcę z bazy.')
            return
        try:
            amount = quantity(self.ilosc.text)
            code = self.kod.text.strip()
            if select_tow_where(code) is False:
                raise ValueError("Taki towar nie występuje w bazie.")
            reserved = sum(line[3] for line in self.lines if line[0] == code)
            available = float(ilo_check(code))
            if available < reserved + amount:
                raise ValueError(f"Za mało towaru {code} na stanie. Dostępne: {available}.")
            self.add_line_from_fields()
        except ValueError as error:
            self.show_alert_dialog(instance, str(error))



    def checked(self, instance_table, current_row):
        found = False
        for item in self.t:
            if item == current_row[0]:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t.remove(current_row[0])
        else:
            # Do something else when no matching element is found
            self.t.append(current_row[0])

    def checked2(self, instance_table, current_row):
        found = False
        for item in self.t2:
            if item == current_row:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t2.remove(current_row)
        else:
            # Do something else when no matching element is found
            self.t2.append(current_row)

class AddScreenPZ(DocumentLinesMixin, Screen):
    t = []
    t2 = []
    text1 = ''
    text2 = ''
    text3 = ''
    towar_pz = []
    towar_pz_all = []
    is_pz = 0

    def __init__(self, dane_tow, dane_pz, **kwargs):
        super().__init__(**kwargs)
        self.lines = []
        self.orientation = 'vertical'
        self.dane_tow = dane_tow
        self.dane_pz = dane_pz
        # Dodaj layout do umieszczenia danych
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        self.dst = PartnerSelectField(self.to_dst, hint_text='Dostawca (wybierz z listy)')
        self.issue_date = MDTextField(hint_text='Data wystawienia (RRRR-MM-DD)', text=today_text())
        self.kod = MDTextField(hint_text='Kod', icon_right = 'language-python')
        self.nazwa = MDTextField(hint_text='Nazwa')
        self.cena = MDTextField(hint_text='Cena netto')
        self.vat = MDTextField(hint_text='VAT %', text='0')
        self.ilosc = MDTextField(hint_text='Ilość')

        layout.add_widget(self.dst)
        layout.add_widget(self.issue_date)
        layout.add_widget(self.kod)
        layout.add_widget(self.nazwa)
        layout.add_widget(self.cena)
        layout.add_widget(self.vat)
        layout.add_widget(self.ilosc)

        self.table = create_table(
            use_pagination=True,
            check=True,
            rows_num=25,
            column_data=[
                ("Kod", dp(30)),
                ("Nazwa", dp(30)),
                ("Cena netto", dp(30)),
                ("Ilość", dp(30)),
                ("VAT %", dp(30)),
                ("Netto", dp(30)),
                ("VAT", dp(30)),
                ("Brutto", dp(30)),
            ],
        )
        layout.add_widget(self.table)
        self.total_label = MDLabel(text=document_totals_text(self.lines))
        layout.add_widget(self.total_label)

        # Przycisk dodaj
        add_button = MDRaisedButton(text="Rejestruj", height=1)
        add_button.bind(on_press=self.add)
        layout.add_widget(add_button)

        # Przycisk nastepny towar
        edit_button = MDRaisedButton(text="Zatwierdz towar/Dodaj kolejny towar", height=1)
        edit_button.bind(on_press=self.save)
        layout.add_widget(edit_button)

        # Przycisk usun
        edit_button = MDRaisedButton(text="Usun", height=1)
        edit_button.bind(on_press=self.delete)
        layout.add_widget(edit_button)

        # Dodaj przycisk Tow
        tow_button = MDRaisedButton(text="Towary", height=1)
        tow_button.bind(on_press=self.to_tow)
        layout.add_widget(tow_button)

        # Dodaj przycisk powrotu
        back_button = MDRaisedButton(text="Powrót", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)

        self.table.bind(on_check_press=self.checked)
        self.table.bind(on_check_press=self.checked2)


        attach_screen_layout(self, layout)


    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = 'menu_PZ'

    def to_tow(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.get_screen('tow_pz_wz').target = self
        self.manager.current = 'tow_pz_wz'

    def to_dst(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.get_screen('dst_to_pz').target = self
        self.manager.current = 'dst_to_pz'





    def show_alert_dialog(self, instance, text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def show_alert_dialogTow(self, instance, text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="Tak",
                    on_release=self.tow_add,
                ),
                MDFlatButton(
                    text="Nie",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def tow_add(self, instance):
        tow_kod = self.kod.text
        nazwa = self.nazwa.text
        ce = self.cena.text
        try:
            x = add_tow(tow_kod, nazwa, ce, self.vat.text)
        except ValueError as error:
            self.dialog_close(instance)
            self.show_alert_dialog(instance, str(error))
            return
        self.dialog_close(instance)
        self.show_alert_dialog(instance, 'Towar został dodany.' if not x else 'Towar o tym kodzie już istnieje.')
    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)

    def delete(self, instance):
        self.delete_selected_lines()

    def add(self, instance):
        if not self.lines:
            self.show_alert_dialog(instance, 'Nie można wystawić PZ bez pozycji.')
            return
        if select_dst_where(self.dst.text.strip()) is False:
            self.show_alert_dialog(instance, 'Wybierz dostawcę z bazy.')
            return
        try:
            document_date = parse_issue_date(self.issue_date.text)
            add_pz(self.lines, self.dst.text.strip(), document_date=document_date)
        except (ValueError, pymysql.MySQLError) as error:
            self.show_alert_dialog(instance, str(error))
            return
        self.lines = []
        self.refresh_lines()
        self.dane_pz.refresh_table()
        self.show_alert_dialog(instance, 'PZ zostało wystawione.')
        self.dst.text = ''
        self.issue_date.text = today_text()
        self.go_back(instance)


    def save(self, instance):
        if select_dst_where(self.dst.text.strip()) is False:
            self.show_alert_dialog(instance, 'Wybierz dostawcę z bazy.')
            return
        try:
            self.add_line_from_fields()
        except ValueError as error:
            self.show_alert_dialog(instance, str(error))



    def checked(self, instance_table, current_row):
        found = False
        for item in self.t:
            if item == current_row[0]:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t.remove(current_row[0])
        else:
            # Do something else when no matching element is found
            self.t.append(current_row[0])

    def checked2(self, instance_table, current_row):
        found = False
        for item in self.t2:
            if item == current_row:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t2.remove(current_row)
        else:
            # Do something else when no matching element is found
            self.t2.append(current_row)

class EditScreenPZ(DocumentLinesMixin, Screen):
    t = []
    t2 = []
    text1 = ''
    text2 = ''
    text3 = ''
    towar_pz = []
    towar_pz_all = []
    is_pz = 0
    pz_p = []

    def __init__(self, dane_tow, menu_pz,  **kwargs):
        super().__init__(**kwargs)
        self.lines = []
        self.document_id = None
        self.orientation = 'vertical'
        self.dane_tow = dane_tow
        self.dane_pz = menu_pz
        # Dodaj layout do umieszczenia danych
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        self.dst = PartnerSelectField(self.to_dst, hint_text='Dostawca (wybierz z listy)')
        self.issue_date = MDTextField(hint_text='Data wystawienia (RRRR-MM-DD)')
        self.kod = MDTextField(hint_text='Kod', icon_right = 'language-python')
        self.nazwa = MDTextField(hint_text='Nazwa')
        self.cena = MDTextField(hint_text='Cena netto')
        self.vat = MDTextField(hint_text='VAT %', text='0')
        self.ilosc = MDTextField(hint_text='Ilość')

        layout.add_widget(self.dst)
        layout.add_widget(self.issue_date)
        layout.add_widget(self.kod)
        layout.add_widget(self.nazwa)
        layout.add_widget(self.cena)
        layout.add_widget(self.vat)
        layout.add_widget(self.ilosc)

        self.table = create_table(
            use_pagination=True,
            check=True,
            rows_num=25,
            column_data=[
                ("Kod", dp(30)),
                ("Nazwa", dp(30)),
                ("Cena netto", dp(30)),
                ("Ilość", dp(30)),
                ("VAT %", dp(30)),
                ("Netto", dp(30)),
                ("VAT", dp(30)),
                ("Brutto", dp(30)),
            ],
        )
        layout.add_widget(self.table)
        self.total_label = MDLabel(text=document_totals_text(self.lines))
        layout.add_widget(self.total_label)

        # Przycisk dodaj
        add_button = MDRaisedButton(text="Rejestruj", height=1)
        add_button.bind(on_press=self.add)
        layout.add_widget(add_button)

        # Przycisk nastepny towar
        edit_button = MDRaisedButton(text="Zatwierdz towar/Dodaj kolejny towar", height=1)
        edit_button.bind(on_press=self.save)
        layout.add_widget(edit_button)

        # Przycisk usun
        edit_button = MDRaisedButton(text="Usun", height=1)
        edit_button.bind(on_press=self.delete)
        layout.add_widget(edit_button)

        # Dodaj przycisk Tow
        tow_button = MDRaisedButton(text="Towary", height=1)
        tow_button.bind(on_press=self.to_tow)
        layout.add_widget(tow_button)

        # Dodaj przycisk powrotu
        back_button = MDRaisedButton(text="Powrót", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)



        attach_screen_layout(self, layout)

        self.table.bind(on_check_press=self.checked)
        self.table.bind(on_check_press=self.checked2)

    def load_document(self, document_id, supplier, document_date, rows):
        self.document_id = document_id
        self.dst.text = supplier
        self.issue_date.text = "" if document_date is None else issue_date_text(document_date)
        self.lines = [
            (str(code), str(name or ""), net_price(money_text(price)),
             quantity(amount), Decimal(str(net)), vat_rate(rate))
            for amount, net, code, name, price, rate in rows
        ]
        self.t = []
        self.t2 = []
        self.refresh_lines()

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.lines = []
        self.refresh_lines()
        self.manager.current = 'menu_PZ'

    def to_tow(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.get_screen('tow_pz_wz').target = self
        self.manager.current = 'tow_pz_wz'

    def to_dst(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.get_screen('dst_to_pz').target = self
        self.manager.current = 'dst_to_pz'





    def show_alert_dialog(self, instance, text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def show_alert_dialogTow(self, instance, text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="Tak",
                    on_release=self.tow_add,
                ),
                MDFlatButton(
                    text="Nie",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def tow_add(self, instance):
        tow_kod = self.kod.text
        nazwa = self.nazwa.text
        ce = self.cena.text
        try:
            x = add_tow(tow_kod, nazwa, ce, self.vat.text)
        except ValueError as error:
            self.dialog_close(instance)
            self.show_alert_dialog(instance, str(error))
            return
        self.dialog_close(instance)
        self.show_alert_dialog(instance, 'Towar został dodany.' if not x else 'Towar o tym kodzie już istnieje.')
    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)

    def delete(self, instance):
        self.delete_selected_lines()

    def add(self, instance):
        if not self.lines:
            self.show_alert_dialog(instance, 'Dokument PZ musi mieć co najmniej jedną pozycję.')
            return
        if select_dst_where(self.dst.text.strip()) is False:
            self.show_alert_dialog(instance, 'Wybierz dostawcę z bazy.')
            return
        try:
            document_date = parse_issue_date(self.issue_date.text)
            edit_pz(self.lines, self.document_id, self.dst.text.strip(), document_date)
        except (ValueError, pymysql.MySQLError) as error:
            self.show_alert_dialog(instance, str(error))
            return
        self.dane_pz.refresh_table()
        self.show_alert_dialog(instance, 'PZ zostało zaktualizowane.')
        self.go_back(instance)


    def save(self, instance):
        if select_dst_where(self.dst.text.strip()) is False:
            self.show_alert_dialog(instance, 'Wybierz dostawcę z bazy.')
            return
        try:
            self.add_line_from_fields()
        except ValueError as error:
            self.show_alert_dialog(instance, str(error))



    def checked(self, instance_table, current_row):
        found = False
        for item in self.t:
            if item == current_row[0]:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t.remove(current_row[0])
        else:
            # Do something else when no matching element is found
            self.t.append(current_row[0])

    def checked2(self, instance_table, current_row):
        found = False
        for item in self.t2:
            if item == current_row:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t2.remove(current_row)
        else:
            # Do something else when no matching element is found
            self.t2.append(current_row)

class EditScreenWZ(DocumentLinesMixin, Screen):
    t = []
    t2 = []
    text1 = ''
    text2 = ''
    text3 = ''
    towar_wz = []
    towar_wz_all = []
    is_wz = 0
    wz_p = []

    def __init__(self, dane_tow, menu_wz,  **kwargs):
        super().__init__(**kwargs)
        self.lines = []
        self.document_id = None
        self.orientation = 'vertical'
        self.dane_tow = dane_tow
        self.dane_wz = menu_wz
        # Dodaj layout do umieszczenia danych
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        self.odb = PartnerSelectField(self.to_odb, hint_text='Odbiorca (wybierz z listy)')
        self.issue_date = MDTextField(hint_text='Data wystawienia (RRRR-MM-DD)')
        self.kod = MDTextField(hint_text='Kod', icon_right = 'language-python')
        self.nazwa = MDTextField(hint_text='Nazwa')
        self.cena = MDTextField(hint_text='Cena netto')
        self.vat = MDTextField(hint_text='VAT %', text='0')
        self.ilosc = MDTextField(hint_text='Ilość')

        layout.add_widget(self.odb)
        layout.add_widget(self.issue_date)
        layout.add_widget(self.kod)
        layout.add_widget(self.nazwa)
        layout.add_widget(self.cena)
        layout.add_widget(self.vat)
        layout.add_widget(self.ilosc)

        self.table = create_table(
            use_pagination=True,
            check=True,
            rows_num=25,
            column_data=[
                ("Kod", dp(30)),
                ("Nazwa", dp(30)),
                ("Cena netto", dp(30)),
                ("Ilość", dp(30)),
                ("VAT %", dp(30)),
                ("Netto", dp(30)),
                ("VAT", dp(30)),
                ("Brutto", dp(30)),
            ],
        )
        layout.add_widget(self.table)
        self.total_label = MDLabel(text=document_totals_text(self.lines))
        layout.add_widget(self.total_label)

        # Przycisk dodaj
        add_button = MDRaisedButton(text="Rejestruj", height=1)
        add_button.bind(on_press=self.add)
        layout.add_widget(add_button)

        # Przycisk nastepny towar
        edit_button = MDRaisedButton(text="Zatwierdz towar/Dodaj kolejny towar", height=1)
        edit_button.bind(on_press=self.save)
        layout.add_widget(edit_button)

        # Przycisk usun
        edit_button = MDRaisedButton(text="Usun", height=1)
        edit_button.bind(on_press=self.delete)
        layout.add_widget(edit_button)

        # Dodaj przycisk Tow
        tow_button = MDRaisedButton(text="Towary", height=1)
        tow_button.bind(on_press=self.to_tow)
        layout.add_widget(tow_button)

        # Dodaj przycisk powrotu
        back_button = MDRaisedButton(text="Powrót", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)



        attach_screen_layout(self, layout)

        self.table.bind(on_check_press=self.checked)
        self.table.bind(on_check_press=self.checked2)

    def load_document(self, document_id, recipient, document_date, rows):
        self.document_id = document_id
        self.odb.text = recipient
        self.issue_date.text = "" if document_date is None else issue_date_text(document_date)
        self.lines = [
            (str(code), str(name or ""), net_price(money_text(price)),
             quantity(amount), Decimal(str(net)), vat_rate(rate))
            for amount, net, code, name, price, rate in rows
        ]
        self.t = []
        self.t2 = []
        self.refresh_lines()

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.lines = []
        self.refresh_lines()
        self.manager.current = 'menu_WZ'

    def to_tow(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.get_screen('tow_pz_wz').target = self
        self.manager.current = 'tow_pz_wz'

    def to_odb(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.get_screen('odb_to_wz').target = self
        self.manager.current = 'odb_to_wz'





    def show_alert_dialog(self, instance, text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def show_alert_dialogTow(self, instance, text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="Tak",
                    on_release=self.tow_add,
                ),
                MDFlatButton(
                    text="Nie",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def tow_add(self, instance):
        tow_kod = self.kod.text
        nazwa = self.nazwa.text
        ce = self.cena.text
        try:
            x = add_tow(tow_kod, nazwa, ce, self.vat.text)
        except ValueError as error:
            self.dialog_close(instance)
            self.show_alert_dialog(instance, str(error))
            return
        self.dialog_close(instance)
        self.show_alert_dialog(instance, 'Towar został dodany.' if not x else 'Towar o tym kodzie już istnieje.')
    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)

    def delete(self, instance):
        self.delete_selected_lines()

    def add(self, instance):
        if not self.lines:
            self.show_alert_dialog(instance, 'Dokument WZ musi mieć co najmniej jedną pozycję.')
            return
        if select_odb_where(self.odb.text.strip()) is False:
            self.show_alert_dialog(instance, 'Wybierz odbiorcę z bazy.')
            return
        try:
            document_date = parse_issue_date(self.issue_date.text)
            edit_wz(self.lines, self.document_id, self.odb.text.strip(), document_date)
        except (ValueError, pymysql.MySQLError) as error:
            self.show_alert_dialog(instance, str(error))
            return
        self.dane_wz.refresh_table()
        self.show_alert_dialog(instance, 'WZ zostało zaktualizowane.')
        self.go_back(instance)


    def save(self, instance):
        if select_odb_where(self.odb.text.strip()) is False:
            self.show_alert_dialog(instance, 'Wybierz odbiorcę z bazy.')
            return
        try:
            self.add_line_from_fields()
        except ValueError as error:
            self.show_alert_dialog(instance, str(error))



    def checked(self, instance_table, current_row):
        found = False
        for item in self.t:
            if item == current_row[0]:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t.remove(current_row[0])
        else:
            # Do something else when no matching element is found
            self.t.append(current_row[0])

    def checked2(self, instance_table, current_row):
        found = False
        for item in self.t2:
            if item == current_row:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t2.remove(current_row)
        else:
            # Do something else when no matching element is found
            self.t2.append(current_row)

class MenuScreenPZ(Screen):
    t = []
    t2 = []
    text1 = ''
    text2 = ''
    text3 = ''
    dane_PZ = []
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        # Dodaj layout do umieszczenia danych
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        # Wyświetl dane z tabeli

        self.table = create_table(
            use_pagination=True,
            check=True,
            rows_num=25,
            column_data=[
                ("Numer", dp(30)),
                ("Data wystawienia", dp(30)),
                ("Wartość netto", dp(30)),
                ("VAT", dp(30)),
                ("Wartość brutto", dp(30)),
                ("Dostawca", dp(30))
            ],
        )
        self.refresh_table()
        layout.add_widget(self.table)

        # Bind tabel
        self.table.bind(on_check_press=self.checked)
        self.table.bind(on_check_press=self.checked2)

        # Przycisk usuń
        del_button = MDRaisedButton(text="Usun Zaznaczone", height=1)
        del_button.bind(on_press=self.delete)
        layout.add_widget(del_button)

        # Przycisk dodaj
        add_button = MDRaisedButton(text="Wystaw PZ", height=1)
        add_button.bind(on_press=self.add)
        layout.add_widget(add_button)

        # Przycisk edytuj
        edit_button = MDRaisedButton(text="Edytuj PZ", height=1)
        edit_button.bind(on_press=self.edit)
        layout.add_widget(edit_button)

        # Dodaj przycisk powrotu
        back_button = MDRaisedButton(text="Powrót", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def refresh_table(self):
        self.dane_PZ = select_PZ2()
        self.table.row_data = [
            (str(number), issue_date_text(document_date), money_text(net),
             money_text(vat), money_text(gross), str(supplier))
            for number, document_date, net, vat, gross, supplier in self.dane_PZ
        ]

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = 'main_menu'

    def delete(self, instance):
        if len(self.t) == 0:
            self.show_alert_dialog(instance, 'PZ nie został wybrany.')
        else:
            for i in self.t:
                delete_PZ(i)
            self.show_alert_dialog(instance, 'PZ została usunięta.')
            self.refresh_table()
            self.t = []

    def show_alert_dialog(self, instance, text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)


    def add(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.get_screen('add_PZ').issue_date.text = today_text()
        self.manager.current = 'add_PZ'

    def edit(self, instance):
        if len(self.t) != 1:
            self.show_alert_dialog(instance, 'Wybierz jeden dokument PZ.')
            return
        document_id = int(self.t[0])
        header, lines = select_pz_edit(document_id)
        if not header:
            self.show_alert_dialog(instance, 'Dokument PZ nie istnieje.')
            return
        self.edit_pz.load_document(document_id, str(header[0][0]), header[0][1], lines)
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.current = 'edit_PZ'


    def checked(self, instance_table, current_row):
        found = False
        for item in self.t:
            if item == current_row[0]:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t.remove(current_row[0])
        else:
            # Do something else when no matching element is found
            self.t.append(current_row[0])

    def checked2(self, instance_table, current_row):
        found = False
        for item in self.t2:
            if item == current_row:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t2.remove(current_row)
        else:
            # Do something else when no matching element is found
            self.t2.append(current_row)

class EditScreenDst(Screen):

    def __init__(self, **kwargs ):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)
        # edit_nazwa = dane_edit.nazwa
        # edit_kod = dane_edit.kod
        # edit_cena = dane_edit.cena
        self.okno = MDLabel(text='Edycjak Dostawcy')
        self.kod = MDLabel(text='',size = (50,50))
        self.nazwa = MDTextField(hint_text='Nazwa', text='')
        self.nip = MDTextField(hint_text='Nip', text='')

        layout.add_widget(self.okno)
        layout.add_widget(self.kod)
        layout.add_widget(self.nazwa)
        layout.add_widget(self.nip)

        button1 = MDRaisedButton(text='Potwierdz Edycje')
        button1.bind(on_press=self.dst_edit)
        layout.add_widget(button1)

        back_button = MDRaisedButton(text="Powrót/anuluj", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def dst_edit(self, instance):
        kod = self.kod.text
        nazwa = self.nazwa.text
        nip = self.nip.text
        kod = kod.replace('Kod: ', '')
        dst_edit(kod, nazwa, nip)
        self.menu_dst.refresh_table()
        self.show_alert_dialog(instance, 'Dostawca ', nazwa, ' został zmodyfikowany')
        self.go_back(instance)

    def show_alert_dialog(self, instance, text, towar, text2):
        self.dialog = MDDialog(
            text=text + towar + text2,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)
    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = 'menu_dst'

class MenuScreenDst(Screen):
    t = []
    t2 = []
    kod = ''
    nip = ''
    nazwa = ''

    def __init__(self,edit_dst, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.edit_dst = edit_dst
        # Dodaj layout do umieszczenia danych
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        # Wyświetl dane z tabeli

        self.table = create_table(
            use_pagination=True,
            check=True,
            rows_num=25,
            column_data=[
                ("Kod", dp(30)),
                ("Nazwa", dp(30)),
                ("Nip", dp(30))
            ],
        )
        self.dane_dst = select_dst2()


        for d in self.dane_dst:
            k, n, ni = d
            self.table.add_row((
                str(k), str(n), str(ni)
            ))

        layout.add_widget(self.table)

        # Bind tabeli
        self.table.bind(on_check_press=self.checked)
        self.table.bind(on_check_press=self.checked2)

        # Przycisk usuń
        del_button = MDRaisedButton(text="Usun Zaznaczone", height=1)
        del_button.bind(on_press=self.delete)
        layout.add_widget(del_button)

        # Przycisk dodaj
        add_button = MDRaisedButton(text="Dodaj dostawce", height=1)
        add_button.bind(on_press=self.add)
        layout.add_widget(add_button)

        # Przycisk edytuj
        edit_button = MDRaisedButton(text="Edytuj dostawce", height=1)
        edit_button.bind(on_press=self.edit)
        layout.add_widget(edit_button)

        # Dodaj przycisk powrotu
        back_button = MDRaisedButton(text="Powrót", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def refresh_table(self):
        self.dane_dst = select_dst2()
        self.table.row_data = [tuple(str(value) for value in row) for row in self.dane_dst]

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = 'main_menu'

    def delete(self, instance):
        if len(self.t) == 0:
            self.show_alert_dialog(instance, 'Towar nie został wybrany')
        else:
            for i in self.t:
                try:
                    delete_dst(i)
                except pymysql.err.IntegrityError as e:
                    if e.args[0] == 1451:
                        self.show_alert_dialog(instance, 'Ten dostawca jest na dokumencie')
                    else:
                        raise

            self.refresh_table()
            self.t = []
            self.t2 = []

    def show_alert_dialog(self, instance, text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)

    def add(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.current = 'add_dst'

    def edit(self, instance):
        if len(self.t) == 0:
            self.show_alert_dialog(instance, 'Towar nie został wybrany')
        else:
            self.manager.transition = SlideTransition(direction='left', duration=0.50)
            self.manager.current = 'edit_dst'
            self.edit_dst.kod.text = 'Kod: ' + self.kod
            self.edit_dst.nazwa.text = self.nazwa
            self.edit_dst.nip.text = self.nip

    def checked(self, instance_table, current_row):
        found = False
        for item in self.t:
            if item == current_row[0]:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t.remove(current_row[0])
        else:
            # Do something else when no matching element is found
            self.t.append(current_row[0])

    def checked2(self, instance_table, current_row):
        found = False
        for item in self.t2:
            if item == current_row:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t2.remove(current_row)
        else:
            # Do something else when no matching element is found
            self.t2.append(current_row)
            self.t3 = self.t2[0]
            self.kod = str(self.t3[0])
            self.nazwa = str(self.t3[1])
            self.nip = str(self.t3[2])

class MenuScreenDstPZ(Screen):
    t = []
    t2 = []
    kod = ''
    nip = ''
    nazwa = ''

    def __init__(self,add_pz, edit_pz, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.add_pz = add_pz
        self.edit_pz = edit_pz
        self.target = add_pz
        # Dodaj layout do umieszczenia danych
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        # Wyświetl dane z tabeli

        self.table = create_table(
            use_pagination=True,
            rows_num=25,
            column_data=[
                ("Kod", dp(30)),
                ("Nazwa", dp(30)),
                ("Nip", dp(30))
            ],
        )
        self.refresh_table()

        layout.add_widget(self.table)

        # Bind tabeli
        self.table.bind(on_row_press=self.do_doc)


        # Dodaj przycisk powrotu
        back_button = MDRaisedButton(text="Powrót", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def refresh_table(self):
        self.dane_dst = select_dst2()
        self.table.row_data = [tuple(str(value) for value in row) for row in self.dane_dst]

    def on_pre_enter(self, *args):
        self.refresh_table()

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = self.target.name

    def do_doc(self, instance_table, instance_row):
        row_num = int(instance_row.index / len(instance_table.column_data))
        row_data = instance_table.row_data[row_num]
        self.target.dst.text = row_data[0]
        self.go_back(instance_table)

class MenuScreenDstWZ(Screen):
    t = []
    t2 = []
    kod = ''
    nip = ''
    nazwa = ''

    def __init__(self,add_wz, edit_wz, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.add_wz = add_wz
        self.edit_wz = edit_wz
        self.target = add_wz
        # Dodaj layout do umieszczenia danych
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        # Wyświetl dane z tabeli

        self.table = create_table(
            use_pagination=True,
            rows_num=25,
            column_data=[
                ("Kod", dp(30)),
                ("Nazwa", dp(30)),
                ("Nip", dp(30))
            ],
        )
        self.refresh_table()

        layout.add_widget(self.table)

        # Bind tabeli
        self.table.bind(on_row_press=self.do_doc)


        # Dodaj przycisk powrotu
        back_button = MDRaisedButton(text="Powrót", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def refresh_table(self):
        self.dane_odb = select_odb2()
        self.table.row_data = [tuple(str(value) for value in row) for row in self.dane_odb]

    def on_pre_enter(self, *args):
        self.refresh_table()

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = self.target.name

    def do_doc(self, instance_table, instance_row):
        row_num = int(instance_row.index / len(instance_table.column_data))
        row_data = instance_table.row_data[row_num]
        self.target.odb.text = row_data[0]
        self.go_back(instance_table)

class AddScreenOdb(SuggestedCodeScreen):
    code_entity = "odb"

    def __init__(self, menu_odb, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        self.menu_odb = menu_odb

        okno = MDLabel(text='Dodanie Odbiorcy')
        self.text1 = MDTextField(hint_text='Kod (można zmienić)')
        self.text2 = MDTextField(hint_text='Nazwa')
        self.text3 = MDTextField(hint_text='Nip')

        layout.add_widget(okno)
        layout.add_widget(self.text1)
        layout.add_widget(self.text2)
        layout.add_widget(self.text3)


        button1 = MDRaisedButton(text='Dodaj')
        button1.bind(on_press=self.odb_add)
        layout.add_widget(button1)

        back_button = MDRaisedButton(text="Powrót/anuluj", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def odb_add(self, instance):
        error = self.code_error()
        if error:
            self.show_alert_dialog(instance, error)
            return

        kod = self.text1.text.strip()
        nazwa = self.text2.text
        nip = self.text3.text
        x = add_odb(kod, nazwa, nip)
        if x is True:
            self.refresh_suggestion_after_duplicate(kod)
            self.show_alert_dialog(instance, "Odbiorca o tym kodzie już istnieje w bazie.")
            return

        self.menu_odb.refresh_table()
        self.go_back(instance)

    def show_alert_dialog(self, instance, text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)

    def go_back(self, instance):
        self.clear_form()
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = 'menu_odb'

class EditScreenOdb(Screen):

    def __init__(self, **kwargs ):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)
        # edit_nazwa = dane_edit.nazwa
        # edit_kod = dane_edit.kod
        # edit_cena = dane_edit.cena
        self.okno = MDLabel(text = 'Edycja Odbiorcy')
        self.kod = MDLabel(text='',size = (50,50))
        self.nazwa = MDTextField(hint_text='Nazwa', text='')
        self.nip = MDTextField(hint_text='Nip', text='')

        layout.add_widget(self.okno)
        layout.add_widget(self.kod)
        layout.add_widget(self.nazwa)
        layout.add_widget(self.nip)

        button1 = MDRaisedButton(text='Potwierdz Edycje')
        button1.bind(on_press=self.odb_edit)
        layout.add_widget(button1)

        back_button = MDRaisedButton(text="Powrót/anuluj", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def odb_edit(self, instance):
        kod = self.kod.text
        nazwa = self.nazwa.text
        nip = self.nip.text
        kod = kod.replace('Kod: ', '')
        odb_edit(kod, nazwa, nip)
        self.menu_odb.refresh_table()
        self.show_alert_dialog(instance, 'Odbiorca ', nazwa, ' został zmodyfikowany')
        self.go_back(instance)

    def show_alert_dialog(self, instance, text, towar, text2):
        self.dialog = MDDialog(
            text=text + towar + text2,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)
    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = 'menu_odb'

class MenuScreenOdb(Screen):
    t = []
    t2 = []
    kod = ''
    nip = ''
    nazwa = ''
    def __init__(self, edit_odb, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.edit_odb = edit_odb
        # Dodaj layout do umieszczenia danych
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        # Wyświetl dane z tabeli

        self.table = create_table(
            use_pagination=True,
            check=True,
            rows_num=25,
            column_data=[
                ("Kod", dp(30)),
                ("Nazwa", dp(30)),
                ("Nip", dp(30))
            ],
        )
        self.dane_odb = select_odb2()


        for d in self.dane_odb:
            k, n, ni = d
            self.table.add_row((
                str(k), str(n), str(ni)
            ))

        layout.add_widget(self.table)

        # Bind tabeli
        self.table.bind(on_check_press=self.checked)
        self.table.bind(on_check_press=self.checked2)

        # Przycisk usuń
        del_button = MDRaisedButton(text="Usun Zaznaczone", height=1)
        del_button.bind(on_press=self.delete)
        layout.add_widget(del_button)

        # Przycisk dodaj
        add_button = MDRaisedButton(text="Dodaj odbiorce", height=1)
        add_button.bind(on_press=self.add)
        layout.add_widget(add_button)

        # Przycisk edytuj
        edit_button = MDRaisedButton(text="Edytuj odbiorce", height=1)
        edit_button.bind(on_press=self.edit)
        layout.add_widget(edit_button)


        # Dodaj przycisk powrotu
        back_button = MDRaisedButton(text="Powrót", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def refresh_table(self):
        self.dane_odb = select_odb2()
        self.table.row_data = [tuple(str(value) for value in row) for row in self.dane_odb]

    def go_back(self, instance):
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = 'main_menu'

    def delete(self, instance):
        if len(self.t) == 0:
            self.show_alert_dialog(instance, 'Towar nie został wybrany')
        else:
            for i in self.t:
                try:
                    delete_odb(i)
                except pymysql.err.IntegrityError as e:
                    if e.args[0] == 1451:
                        self.show_alert_dialog(instance, 'Ten dostawca jest na dokumencie')
                    else:
                        raise

            self.refresh_table()
            self.t = []
            self.t2 = []

    def show_alert_dialog(self, instance, text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)


    def add(self, instance):
        self.manager.transition = SlideTransition(direction='left', duration=0.50)
        self.manager.current = 'add_odb'

    def edit(self, instance):
        if len(self.t) == 0:
            self.show_alert_dialog(instance, 'Towar nie został wybrany')
        else:
            self.manager.transition = SlideTransition(direction='left', duration=0.50)
            self.manager.current = 'edit_odb'
            self.edit_odb.kod.text = 'Kod: ' + self.kod
            self.edit_odb.nazwa.text = self.nazwa
            self.edit_odb.nip.text = self.nip


    def checked(self, instance_table, current_row):
        found = False
        for item in self.t:
            if item == current_row[0]:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t.remove(current_row[0])
        else:
            # Do something else when no matching element is found
            self.t.append(current_row[0])

    def checked2(self, instance_table, current_row):
        found = False
        for item in self.t2:
            if item == current_row:
                found = True
                break
        if found:
            # Do something when a matching element is found
            self.t2.remove(current_row)
        else:
            # Do something else when no matching element is found
            self.t2.append(current_row)
            self.t3 = self.t2[0]
            self.kod = str(self.t3[0])
            self.nazwa = str(self.t3[1])
            self.nip = str(self.t3[2])

class AddScreenDst(SuggestedCodeScreen):
    code_entity = "dst"

    def __init__(self, menu_dst, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)

        self.menu_dst = menu_dst

        okno = MDLabel(text='Dodanie Dostawcy')
        self.text1 = MDTextField(hint_text='Kod (można zmienić)')
        self.text2 = MDTextField(hint_text='Nazwa')
        self.text3 = MDTextField(hint_text='Nip')

        layout.add_widget(okno)
        layout.add_widget(self.text1)
        layout.add_widget(self.text2)
        layout.add_widget(self.text3)


        button1 = MDRaisedButton(text='Dodaj')
        button1.bind(on_press=self.dst_add)
        layout.add_widget(button1)

        back_button = MDRaisedButton(text="Powrót/anuluj", height=1)
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)
        attach_screen_layout(self, layout)

    def dst_add(self, instance):
        error = self.code_error()
        if error:
            self.show_alert_dialog(instance, error)
            return

        kod = self.text1.text.strip()
        nazwa = self.text2.text
        nip = self.text3.text
        x = add_dst(kod, nazwa, nip)
        if x is True:
            self.refresh_suggestion_after_duplicate(kod)
            self.show_alert_dialog(instance, "Dostawca o tym kodzie już istnieje w bazie.")
            return

        self.menu_dst.refresh_table()
        self.go_back(instance)

    def show_alert_dialog(self, instance, text):
        self.dialog = MDDialog(
            text=text,
            buttons=[
                MDFlatButton(
                    text="OK",
                    on_release=self.dialog_close,
                ),
            ], )
        self.dialog.open()

    def dialog_close(self, instance):
        self.dialog.dismiss(force=True)

    def go_back(self, instance):
        self.clear_form()
        self.manager.transition = SlideTransition(direction='right', duration=0.50)
        self.manager.current = 'menu_dst'



class MainApp(MDApp):
    def toggle_theme(self):
        style = "Light" if self.theme_cls.theme_style == "Dark" else "Dark"
        self.theme_cls.theme_style = style
        apply_palette(self.screen_manager, style)
        self.main_menu_screen.theme_button.text = (
            "Tryb nocny" if style == "Light" else "Tryb dzienny"
        )
        try:
            save_theme(style)
        except OSError as error:
            dialog = MDDialog(
                text=f"Nie udało się zapisać ustawienia motywu: {error}",
                buttons=[MDFlatButton(text="OK", on_release=lambda _button: dialog.dismiss())],
            )
            dialog.open()

    def build(self):
        Window.minimum_width = 900
        Window.minimum_height = 640
        Window.size = (1100, 720)
        self.theme_cls.theme_style = load_theme()
        self.theme_cls.primary_palette = "Blue"
        set_palette(self.theme_cls.theme_style)

        screen_manager = ScreenManager()

        main_menu_screen = MainMenu(name='main_menu')
        main_menu_screen.app = self
        main_menu_screen.theme_button.text = (
            "Tryb nocny" if self.theme_cls.theme_style == "Light" else "Tryb dzienny"
        )
        edit_screen_tow = EditScreenTow(name='edit_tow')
        tow_select_screen = TowSelectScreen(name='tow_select', dane_edit = edit_screen_tow)
        menu_screen_wz = WZScreen(name='menu_WZ')
        menu_screen_pz = MenuScreenPZ(name='menu_PZ')
        edit_screen_odb = EditScreenOdb(name='edit_odb')
        edit_screen_dst = EditScreenDst(name='edit_dst')
        menu_screen_dst = MenuScreenDst(name='menu_dst', edit_dst = edit_screen_dst)
        menu_screen_odb = MenuScreenOdb(name='menu_odb', edit_odb = edit_screen_odb)
        add_screen_tow = AddScreenTow(name='add_tow', menu_tow = tow_select_screen)
        add_screen_odb = AddScreenOdb(name='add_odb', menu_odb = menu_screen_odb)
        add_screen_dst = AddScreenDst(name='add_dst', menu_dst = menu_screen_dst)
        add_screen_WZ = AddScreenWZ(name='add_WZ', dane_tow=tow_select_screen, dane_wz = menu_screen_wz)
        add_screen_PZ = AddScreenPZ(name='add_PZ', dane_tow=tow_select_screen, dane_pz = menu_screen_pz)
        edit_screen_pz = EditScreenPZ(name = 'edit_PZ', dane_tow=tow_select_screen, menu_pz = menu_screen_pz)
        edit_screen_wz = EditScreenWZ(name = 'edit_WZ', dane_tow=tow_select_screen, menu_wz = menu_screen_wz)
        tow_to_pz = TowSelectScreenToPZ(name='tow_pz_wz', add_pz=add_screen_PZ, add_wz=add_screen_WZ, edit_pz = edit_screen_pz)
        dst_to_pz = MenuScreenDstPZ(name='dst_to_pz', add_pz=add_screen_PZ, edit_pz = edit_screen_pz)
        odb_to_wz = MenuScreenDstWZ(name='odb_to_wz', add_wz=add_screen_WZ, edit_wz = edit_screen_wz)

        edit_screen_tow.menu_tow = tow_select_screen
        edit_screen_dst.menu_dst = menu_screen_dst
        edit_screen_odb.menu_odb = menu_screen_odb
        menu_screen_pz.edit_pz = edit_screen_pz
        menu_screen_wz.edit_wz = edit_screen_wz
        add_screen_PZ.tow_do_pz = tow_to_pz


        

        screen_manager.add_widget(main_menu_screen)
        screen_manager.add_widget(add_screen_tow)
        screen_manager.add_widget(edit_screen_tow)
        screen_manager.add_widget(edit_screen_odb)
        screen_manager.add_widget(edit_screen_dst)
        screen_manager.add_widget(add_screen_odb)
        screen_manager.add_widget(add_screen_WZ)
        screen_manager.add_widget(add_screen_PZ)
        screen_manager.add_widget(add_screen_dst)
        screen_manager.add_widget(menu_screen_wz)
        screen_manager.add_widget(menu_screen_pz)
        screen_manager.add_widget(menu_screen_dst)
        screen_manager.add_widget(menu_screen_odb)
        screen_manager.add_widget(tow_select_screen)
        screen_manager.add_widget(tow_to_pz)
        screen_manager.add_widget(odb_to_wz)
        screen_manager.add_widget(dst_to_pz)
        screen_manager.add_widget(edit_screen_pz)
        screen_manager.add_widget(edit_screen_wz)

        self.screen_manager = screen_manager
        self.main_menu_screen = main_menu_screen
        return screen_manager


if __name__ == '__main__':
    try:
        MainApp().run()
    finally:
        mydb.close()
