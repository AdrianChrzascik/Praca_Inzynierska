# WMS — instalacja na Windows

## Dla użytkownika

1. Rozpakuj `WMS-Setup.zip` na komputerze z Windows 10/11 x64. Nie uruchamiaj pliku bezpośrednio z podglądu ZIP.
2. Kliknij dwukrotnie `Zainstaluj-WMS.cmd` i zaakceptuj monit Windows o uprawnienia administratora.
3. Jeśli otworzy się instalator MariaDB, ustaw hasło użytkownika `root` oraz włącz instalację i uruchamianie usługi. Następnie wpisz hasło `root` w oknie instalatora WMS. Przy istniejącej usłudze MariaDB/MySQL wpisz jej obecne hasło `root`.
4. Po zakończeniu instalacji uruchom **WMS** z menu Start.

Instalator wykrywa istniejącą usługę MariaDB/MySQL i uruchamia ją, jeśli jest zatrzymana. Nie instaluje wtedy drugiego serwera. Usługa musi nasłuchiwać na `127.0.0.1:3306`. Połączenie z internetem i WinGet są potrzebne tylko wtedy, gdy takiej usługi nie ma. Bez WinGet najpierw zainstaluj MariaDB Server 11.8 LTS z usługą, a potem ponownie uruchom `Zainstaluj-WMS.cmd`.

Instalator kopiuje aplikację do `C:\Program Files\WMS`, tworzy skrót w menu Start oraz przygotowuje lokalną bazę danych. Nie przenoś samego `WMS.exe` — potrzebuje plików z folderu `WMS`.

Po aktualizacji dodającej VAT uruchom `Zainstaluj-WMS.cmd` ponownie. Instalator doda brakujące kolumny VAT bez usuwania rekordów. Istniejące towary i pozycje dokumentów otrzymają stawkę `0%`; uzupełnij właściwe stawki w edycji towarów. Cena towaru jest ceną netto, a dokumenty doliczają VAT i pokazują sumy netto, VAT oraz brutto. Każda pozycja dokumentu zapamiętuje stawkę używaną przy jej zapisie.

## Przygotowanie paczki

Na Windows x64 z Pythonem 3.12 x64 i dostępem do internetu uruchom w katalogu projektu:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Gotowa paczka to `dist\WMS-Setup.zip`. Przekaż użytkownikowi tylko ten plik. Build używa wersji bibliotek przypiętych w `requirements.txt` i `requirements-build.txt`. Sprawdź gotową paczkę na czystym Windowsie x64, ponieważ Kivy/KivyMD używają natywnych bibliotek systemowych.

## Bezpieczeństwo i istniejące dane

`installer\schema.sql` używa `CREATE ... IF NOT EXISTS` i nie usuwa tabel. Hasło `root` nie jest zapisywane w konfiguracji WMS; jest potrzebne do przygotowania bazy. Aplikacja używa konta `wms_app` z losowym hasłem i uprawnieniami SELECT/INSERT/UPDATE/DELETE do bazy `mydb`.

Nie uruchamiaj `Baza_SQL.sql` jako instalatora: ten plik zawiera `DROP TABLE` i może skasować istniejące dane. Instalator dodaje kolumny VAT do istniejących tabel, lecz nie migruje automatycznie innych, starszych różnic struktury. Przy takiej bazie najpierw wykonaj kopię zapasową i sprawdź schemat.

Plik połączenia jest zapisywany jako `%ProgramData%\WMS\database.ini`. Można wskazać inną lokalizację zmienną środowiskową `WMS_CONFIG_PATH`. Przy błędzie połączenia program wyświetla komunikat z lokalizacją konfiguracji i szczegółami sterownika.

## Ręczne uruchomienie instalatora

Jeśli potrzebujesz zmienić folder programu, uruchom `installer\Install-WMS.ps1` w PowerShellu jako administrator, podając parametr `-InstallDirectory`. Parametr `-ApplicationSource` wskazuje folder z całym programem, w tym `WMS.exe`.
