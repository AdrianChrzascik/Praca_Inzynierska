$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw "Nie znaleziono Python 3.12 w PATH. Zainstaluj Python 3.12 x64 i uruchom build.ps1 ponownie."
}
$pythonVersion = & $pythonCommand.Source --version
if ($pythonVersion -notmatch "Python 3\.12\.") {
    throw "Build wymaga Python 3.12 x64 (wykryto: $pythonVersion)."
}
$pythonBits = & $pythonCommand.Source -c "import struct; print(struct.calcsize('P') * 8)"
if ($pythonBits -ne "64") {
    throw "Build wymaga 64-bitowego Pythona (wykryto: $pythonBits-bit)."
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $pythonCommand.Source -m venv (Join-Path $PSScriptRoot ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Nie udało się utworzyć środowiska build." }
}

& $venvPython -m pip install -r (Join-Path $PSScriptRoot "requirements-build.txt")
if ($LASTEXITCODE -ne 0) { throw "Nie udało się zainstalować zależności build." }

$env:KIVY_NO_FILELOG = "1"
$env:KIVY_LOG_MODE = "MIXED"
$env:KCFG_KIVY_LOG_LEVEL = "warning"
& $venvPython -m PyInstaller --noconfirm --clean (Join-Path $PSScriptRoot "main.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller nie zbudował aplikacji." }

$distributionDirectory = Join-Path $PSScriptRoot "dist"
$distributionInstaller = Join-Path $distributionDirectory "installer"
New-Item -Path $distributionInstaller -ItemType Directory -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "installer\Install-WMS.ps1") -Destination $distributionInstaller -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "installer\Run-Installer.ps1") -Destination $distributionInstaller -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "installer\schema.sql") -Destination $distributionInstaller -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README_INSTALACJA.md") -Destination $distributionInstaller -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README_INSTALACJA.md") -Destination $distributionDirectory -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "CHANGELOG.md") -Destination $distributionDirectory -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "Zainstaluj-WMS.cmd") -Destination $distributionDirectory -Force

$applicationDirectory = Join-Path $distributionDirectory "WMS"
if (-not (Test-Path -LiteralPath (Join-Path $applicationDirectory "WMS.exe"))) {
    throw "Build zakonczyl sie bez pliku WMS.exe."
}

$packagePath = Join-Path $distributionDirectory "WMS-Setup.zip"
Compress-Archive -LiteralPath @(
    $applicationDirectory,
    $distributionInstaller,
    (Join-Path $distributionDirectory "README_INSTALACJA.md"),
    (Join-Path $distributionDirectory "CHANGELOG.md"),
    (Join-Path $distributionDirectory "Zainstaluj-WMS.cmd")
) -DestinationPath $packagePath -Force

Write-Host "Paczka instalacyjna: $packagePath" -ForegroundColor Green
