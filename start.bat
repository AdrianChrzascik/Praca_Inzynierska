@echo off
set "APP=%~dp0dist\WMS\WMS.exe"
if not exist "%APP%" (
	echo Nie znaleziono gotowego programu. Uruchom build.ps1, aby go zbudowac.
	pause
	exit /b 1
)
start "" "%APP%"
