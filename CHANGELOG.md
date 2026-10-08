# Historia zmian

Każdy wpis opisuje zmianę i powód jej wprowadzenia.

## 2026-10-08

### Komunikaty błędów i motyw

- **Zmiana:** Komunikaty w działającym programie korzystają ze wspólnego okna w kolorach WMS, z nagłówkiem, zaokrąglonymi narożnikami i przyciskami dopasowanymi do motywu. Błędy połączenia wyświetlane przed uruchomieniem GUI mają osobne okno w tych samych kolorach. **Powód:** Błędy są czytelne i wyglądają spójnie z aplikacją także wtedy, gdy baza uniemożliwia uruchomienie KivyMD.
- **Zmiana:** Przy braku konfiguracji bazy, koniecznej aktualizacji schematu lub błędzie połączenia okno startowe udostępnia „Uruchom instalator”, gdy komplet jego plików znajduje się obok programu. Instalator kopiuje te pliki do katalogu zainstalowanej aplikacji i potrafi uruchomić naprawę z tego katalogu. **Powód:** Użytkownik może od razu wykonać instalację, migrację lub ponowne przygotowanie połączenia bez szukania pliku w rozpakowanej paczce.
- **Zmiana:** W menu głównym dodano przełącznik trybu dziennego i nocnego; kolory ekranów, tabel, przycisków i okien są zmieniane podczas pracy, a wybór jest zapisywany dla użytkownika. **Powód:** Interfejs można dopasować do oświetlenia i preferencji bez ponownego uruchamiania programu.
- **Zmiana:** Uzupełniono instrukcję oraz testy ustawień wyglądu i wykrywania instalatora. **Powód:** Nowe działania muszą być łatwe do znalezienia i sprawdzane bez wykonywania instalacji na danych użytkownika.

### Daty towarów i dokumentów

- **Zmiana:** Towar otrzymuje automatyczną datę i godzinę dodania, a edycja jego nazwy, ceny lub VAT zapisuje datę i godzinę ostatniej edycji. Obie informacje widać w tabeli towarów i formularzu edycji. **Powód:** Można sprawdzić, kiedy założono kartę towaru i kiedy ostatnio zmieniono jej dane, bez ręcznego wpisywania dat.
- **Zmiana:** Formularze tworzenia PZ/WZ podpowiadają dzisiejszą datę wystawienia; przy tworzeniu i edycji można wpisać inną poprawną datę w formacie `RRRR-MM-DD`. Daty są zapisywane i pokazywane w listach dokumentów. **Powód:** Dokument zachowuje właściwą datę operacji, także gdy jest wystawiany później lub korygowany.
- **Zmiana:** Instalator dodaje brakujące kolumny dat bez usuwania danych, a aplikacja sygnalizuje potrzebę aktualizacji bazy. Istniejące rekordy pozostają bez dat historycznych; przy edycji starego dokumentu trzeba je uzupełnić. **Powód:** Nie można wiarygodnie odtworzyć dat wcześniejszych operacji na podstawie obecnych danych.
- **Zmiana:** Uzupełniono instrukcję instalacji oraz testy poprawności dat i zapisu dokumentów. **Powód:** Format daty i sposób aktualizacji bazy muszą być jasne, a błędna data nie może trafić do dokumentu.

### Wybór kontrahenta w dokumentach

- **Zmiana:** Usunięto osobne przyciski „Dostawcy” i „Odbiorcy” z formularzy dodawania i edycji PZ/WZ. Ikona po prawej stronie pola kontrahenta otwiera dotychczasową listę, a wybrany kod wraca do pola; kod można nadal wpisać ręcznie. **Powód:** Wybór kontrahenta jest dostępny przy polu, którego dotyczy, bez dodatkowego przycisku w sekcji działań dokumentu.
- **Zmiana:** Układ formularza zachowuje ikonę wyboru kontrahenta, usuwając tylko zbędną ikonę Pythona z innych pól. **Powód:** Akcja wyboru musi pozostać widoczna po zbudowaniu ekranu.

### VAT w towarach i dokumentach

- **Zmiana:** Dodano stawkę VAT przy tworzeniu i edycji towaru; dotychczasowa cena jest ceną netto. Formularze sprawdzają poprawność ceny i stawki. **Powód:** Użytkownik może przypisać towarowi właściwy podatek bez ręcznego wyliczania ceny brutto.
- **Zmiana:** Edycja towaru odczytuje wybrany rekord z aktualnej tabeli i pokazuje komunikat, gdy nie zaznaczono dokładnie jednego towaru. **Powód:** Pierwsze kliknięcie „Edytuj towar” nie może kończyć się błędem ani pobierać nieaktualnej stawki VAT z wcześniejszego zaznaczenia.
- **Zmiana:** Przy wystawianiu i edycji PZ oraz WZ formularz podpowiada cenę netto i stawkę VAT wybranego towaru, pozwala je zmienić dla pozycji i pokazuje netto, VAT oraz brutto dla pozycji i całego dokumentu. Obliczenia pieniężne używają liczb dziesiętnych i zaokrąglenia do grosza. **Powód:** Kwoty dokumentu są widoczne przed zapisem i nie zależą od niedokładności liczb zmiennoprzecinkowych.
- **Zmiana:** Stawka VAT jest zapisywana osobno przy każdej pozycji dokumentu, a zestawienia PZ/WZ wyliczają podatek z zapisanych stawek. **Powód:** Późniejsza zmiana stawki na towarze nie zmienia wartości wcześniej wystawionych dokumentów.
- **Zmiana:** Nowe i edytowane dokumenty zapisują pozycje oraz zmiany stanu magazynowego w jednej transakcji; numer nowego dokumentu pochodzi z bazy. Zapis pustego dokumentu jest odrzucany. **Powód:** Błąd zapisu nie może pozostawić częściowo zmienionych stanów, a równoczesne wystawienie dokumentów nie powinno użyć tego samego numeru.
- **Zmiana:** Schemat nowej instalacji zawiera kolumny VAT, a ponowne uruchomienie instalatora dodaje je do istniejącej bazy. Dotychczasowe rekordy otrzymują 0% i wymagają ustawienia właściwych stawek; aplikacja informuje, jeśli baza nie została zaktualizowana. **Powód:** Aktualizacja nie usuwa istniejących danych ani nie zgaduje historycznych stawek podatku.
- **Zmiana:** Zaktualizowano instrukcję instalacji i dodano testy obliczeń VAT oraz zapisu dokumentów. **Powód:** Kroki aktualizacji i zasady liczenia są udokumentowane, a kluczowe obliczenia i cofanie błędnego zapisu są sprawdzane automatycznie.

### Odświeżanie tabel

- **Zmiana:** Po dodaniu, edycji lub usunięciu towaru, odbiorcy i dostawcy odpowiednia tabela pobiera aktualne dane z bazy i zastępuje całą listę wierszy. **Powód:** Usuwanie pojedynczych wierszy według zapamiętanej kopii wymagało dokładnego dopasowania; po dodaniu towaru mogło zakończyć się błędem `ValueError: list.remove(x): x not in list`.

### Numeracja kodów

- **Zmiana:** Formularze nowego towaru, odbiorcy i dostawcy podpowiadają najwyższy istniejący kod liczbowy plus jeden przy każdym otwarciu. Etykieta pola informuje, że kod można zmienić ręcznie; tekstowe kody towarów pozostają dostępne. **Powód:** Przyspiesza to dodawanie rekordów bez odbierania możliwości użycia własnego kodu i bez zmiany istniejącego schematu bazy.
- **Zmiana:** Formularze sprawdzają poprawność kodu przed zapisem; przy zajętym kodzie pozostają otwarte, a automatyczna propozycja jest odświeżana. Zapis rozpoznaje konflikt również wtedy, gdy kod zostanie zajęty po wyświetleniu podpowiedzi. **Powód:** Błędny lub powielony kod nie powinien zamykać formularza ani powodować awarii aplikacji.
- **Zmiana:** Po dodaniu rekordu odświeżana jest także lista zapamiętana przez ekran tabeli. **Powód:** Kolejne dodawanie nie powinno powielać wierszy w widoku.
- **Zmiana:** Dodano testy wyznaczania następnego kodu, zapisu kodu ręcznego i obsługi duplikatu. **Powód:** Te zachowania są kluczowe dla poprawnego numerowania i powinny być sprawdzane po zmianach kodu.

### Interfejs użytkownika

- **Zmiana:** Ujednolicono układ 19 ekranów; nagłówek, formularz, tabela i akcje mają wyznaczone miejsca. **Powód:** Łatwiej znaleźć potrzebne informacje i przyciski na różnych ekranach.
- **Zmiana:** Powiększono przyciski, które wcześniej miały wysokość jednego piksela, i rozmieszczono akcje w maksymalnie czterech kolumnach. **Powód:** Przyciski są czytelne i dostępne przy różnych szerokościach okna.
- **Zmiana:** Uporządkowano menu główne w dwóch kolumnach oraz ustawiono początkowy rozmiar okna na 1100 × 720 pikseli. **Powód:** Menu i podstawowe ekrany mieszczą się w oknie bez ręcznego powiększania.
- **Zmiana:** Dopasowano szerokości kolumn tabel do danych oraz ujednolicono kolory nagłówków, wierszy i zaznaczenia. **Powód:** Wartości są łatwiejsze do odczytania, a wybrany wiersz łatwiej rozpoznać.
- **Zmiana:** Pola formularzy układają się w jednej lub dwóch kolumnach zależnie od szerokości okna; ujednolicono ich wygląd i usunięto ikonę Pythona z pola kodu. **Powód:** Formularze pozostają czytelne także w węższym oknie, a ikona nie sugeruje błędnego znaczenia pola.
- **Zmiana:** Poprawiono etykiety, między innymi „Dodaj pozycję”, „Usuń zaznaczone”, „Zapisz dokument” i „NIP”. **Powód:** Nazwy wyraźniej opisują działanie przycisków i zawartość pól.

### Dokumentacja

- **Zmiana:** Uzupełniono historię zmian o wcześniejsze prace oraz powód przy każdym wpisie; aktualny plik dołączono do paczki instalacyjnej. **Powód:** Użytkownik może sprawdzić, co zmieniono i dlaczego, także po rozpakowaniu paczki.

## 2026-10-07

### Instalacja i pakowanie

- **Zmiana:** Przygotowano paczkę `WMS-Setup.zip` z aplikacją, instalatorem i instrukcją oraz uruchamianie instalacji przez `Zainstaluj-WMS.cmd`. **Powód:** Instalacja wymaga rozpakowania jednej paczki i uruchomienia jednego pliku.
- **Zmiana:** Instalator sam prosi Windows o uprawnienia administratora, kopiuje aplikację do `Program Files\WMS` i tworzy skrót w menu Start. **Powód:** Nie trzeba ręcznie uruchamiać PowerShella jako administrator ani szukać pliku programu po instalacji.
- **Zmiana:** Dodano skrypt budowania aplikacji i paczki oraz przypięto wersje zależności. **Powód:** Kolejne paczki można przygotować w ten sam sposób i ograniczyć problemy wynikające ze zmiany wersji bibliotek.
- **Zmiana:** Dołączono zasoby KivyMD do programu zbudowanego przez PyInstaller i zmieniono `start.bat`, aby uruchamiał gotowy program. **Powód:** Aplikacja potrzebuje tych zasobów po spakowaniu, a uruchomienie nie powinno za każdym razem instalować bibliotek Pythona.
- **Zmiana:** Dodano `README_INSTALACJA.md` z krokami instalacji, wymaganiami i opisem istniejących danych. **Powód:** Osoba instalująca WMS może przejść proces bez znajomości skryptów projektu.

### MariaDB/MySQL i konfiguracja

- **Zmiana:** Instalator wykrywa istniejącą usługę MariaDB lub MySQL, wybiera działającą usługę i uruchamia zatrzymaną; gdy usługi brak, uruchamia instalator MariaDB przez WinGet. **Powód:** Na komputerze z działającą bazą nie trzeba instalować drugiego serwera.
- **Zmiana:** Instalator szuka klienta `mariadb.exe` lub `mysql.exe` przy wykrytej usłudze, w katalogach instalacyjnych i w `PATH`. **Powód:** Klient może znajdować się poza standardową lokalizacją.
- **Zmiana:** Instalator tworzy brakującą bazę i tabele bez usuwania istniejących danych, przygotowuje konto `wms_app` i zapisuje konfigurację w `%ProgramData%\WMS\database.ini`. **Powód:** Aplikacja może korzystać z osobnego konta bez zapisanego na stałe hasła `root`, a ponowna instalacja nie powinna kasować tabel.
- **Zmiana:** Połączenie aplikacji z bazą odczytuje `database.ini` oraz pozwala wskazać plik przez `WMS_CONFIG_PATH`; błędy połączenia są wyświetlane w komunikacie. **Powód:** Dane dostępowe działają w instalacji i podczas uruchamiania ze źródeł, a problem z konfiguracją można rozpoznać bez konsoli.
- **Zmiana:** Poprawiono tworzenie reguły ACL dla tymczasowego pliku z hasłem `root`: flagi dziedziczenia są obliczane osobno przed wywołaniem konstruktora. **Powód:** Instalacja kończyła się błędem PowerShella `System.Object[] does not contain a method named 'op_BitwiseOr'`.

### Zgodność bibliotek

- **Zmiana:** Ustalono `KivyMD==1.2.0` i przebudowano aplikację. **Powód:** Kod używa `MDRaisedButton`, `MDFlatButton` i starszego API dialogów, których zainstalowana wersja KivyMD 2.0 nie udostępniała; aplikacja kończyła się błędem `ImportError` przy starcie.
