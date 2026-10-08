[CmdletBinding()]
param(
    [string]$ApplicationSource = (Join-Path $PSScriptRoot "..\WMS"),
    [string]$InstallDirectory = (Join-Path $env:ProgramFiles "WMS")
)

$ErrorActionPreference = "Stop"
$MariaDbVersion = "11.8.2.0"
$DatabaseName = "mydb"
$DatabaseUser = "wms_app"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-DatabaseService {
    $services = @(Get-Service -ErrorAction Stop | Where-Object {
        $_.Name -match '^(MariaDB|MySQL)(?:$|[0-9._-])' -or
        $_.DisplayName -match '^(MariaDB|MySQL)(?:$|\s+Server\b|\s+[0-9])'
    })

    if ($services.Count -eq 0) { return $null }

    # Prefer a service that is already running when several database versions exist.
    return $services |
        Sort-Object @{ Expression = { if ($_.Status -eq 'Running') { 0 } else { 1 } } }, Name |
        Select-Object -First 1
}

function Get-DatabaseClient($Service) {
    $servicePath = "HKLM:\SYSTEM\CurrentControlSet\Services\$($Service.Name)"
    $imagePath = (Get-ItemProperty -LiteralPath $servicePath -Name ImagePath -ErrorAction SilentlyContinue).ImagePath
    if ($imagePath -match '^\s*"(?<exe>[^"]+\.exe)"' -or
        $imagePath -match '^\s*(?<exe>.+?\.exe)(?:\s|$)') {
        $serverDirectory = Split-Path -Parent ([Environment]::ExpandEnvironmentVariables($Matches.exe))
        foreach ($clientName in @('mariadb.exe', 'mysql.exe')) {
            $candidate = Join-Path $serverDirectory $clientName
            if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
        }
    }

    $programFilesRoots = @($env:ProgramW6432, $env:ProgramFiles, ${env:ProgramFiles(x86)}) |
        Where-Object { $_ } | Select-Object -Unique
    foreach ($root in $programFilesRoots) {
        foreach ($folder in @('MariaDB*', 'MySQL*')) {
            foreach ($clientName in @('mariadb.exe', 'mysql.exe')) {
                $candidate = Get-ChildItem -Path (Join-Path $root $folder) -Filter $clientName -File -Recurse -ErrorAction SilentlyContinue |
                    Select-Object -First 1 -ExpandProperty FullName
                if ($candidate) { return $candidate }
            }
        }
    }

    $command = Get-Command mariadb.exe,mysql.exe -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($command) { return $command.Source }
    return $null
}

function ConvertTo-PlainText([Security.SecureString]$Value) {
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

if (-not (Test-IsAdministrator)) {
    throw "Run Install-WMS.ps1 as Administrator."
}

$source = $null
foreach ($candidate in @(
    $ApplicationSource,
    (Join-Path $PSScriptRoot ".."),
    (Join-Path $PSScriptRoot "..\dist\WMS")
)) {
    if (Test-Path -LiteralPath (Join-Path $candidate "WMS.exe") -PathType Leaf) {
        $source = (Resolve-Path -LiteralPath $candidate).Path
        break
    }
}
if (-not $source) {
    throw "WMS.exe was not found near the installer. Build the application first by running build.ps1."
}
$schemaPath = Join-Path $PSScriptRoot "schema.sql"
if (-not (Test-Path -LiteralPath $schemaPath)) {
    throw "schema.sql is missing next to the installer script."
}

$databaseService = Get-DatabaseService
if (-not $databaseService) {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw "No MariaDB/MySQL service or winget was found. Install MariaDB Server 11.8 LTS with its service, then run this installer again."
    }

    Write-Host "Starting the MariaDB Server 11.8 LTS installer." -ForegroundColor Cyan
    Write-Host "In the wizard, set the root password and enable installation/startup of the MariaDB service."
    & winget.exe install --id MariaDB.Server --exact --version $MariaDbVersion --interactive --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) { throw "MariaDB installer exited with code $LASTEXITCODE." }

    $databaseService = Get-DatabaseService
}
if (-not $databaseService) {
    throw "No MariaDB/MySQL service was created. Check the database server installation and run this installer again."
}
$databaseService.Refresh()
Write-Host "Using database service: $($databaseService.Name) ($($databaseService.Status))." -ForegroundColor Cyan
if ($databaseService.Status -ne "Running") {
    Start-Service -Name $databaseService.Name
    $databaseService.WaitForStatus("Running", [TimeSpan]::FromSeconds(30))
}

$dbClient = Get-DatabaseClient $databaseService
if (-not $dbClient) {
    $dbClient = Read-Host "Enter the full path to mariadb.exe or mysql.exe"
}
if (-not (Test-Path -LiteralPath $dbClient -PathType Leaf)) { throw "Database client not found: $dbClient" }

$rootSecure = Read-Host "Enter the root password for $($databaseService.Name)" -AsSecureString
$rootPassword = ConvertTo-PlainText $rootSecure
$appPassword = ([Guid]::NewGuid().ToString("N") + [Guid]::NewGuid().ToString("N"))
$tempDirectory = Join-Path $env:TEMP ("WMS-Setup-" + [Guid]::NewGuid().ToString("N"))
New-Item -Path $tempDirectory -ItemType Directory | Out-Null
$defaultsFile = Join-Path $tempDirectory "client.cnf"
$bootstrapFile = Join-Path $tempDirectory "bootstrap.sql"

try {
    $escapedRootPassword = $rootPassword.Replace("\", "\\").Replace('"', '\"')
    Set-Content -LiteralPath $defaultsFile -Encoding ASCII -Value "[client]`r`nuser=root`r`npassword=`"$escapedRootPassword`"`r`nhost=127.0.0.1`r`nport=3306`r`n"

    $acl = Get-Acl -LiteralPath $tempDirectory
    $acl.SetAccessRuleProtection($true, $false)
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $inheritanceFlags = [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
        [Security.AccessControl.InheritanceFlags]::ObjectInherit
    $fullControl = [Security.AccessControl.FileSystemAccessRule]::new(
        $currentUser,
        [Security.AccessControl.FileSystemRights]::FullControl,
        $inheritanceFlags,
        [Security.AccessControl.PropagationFlags]::None,
        [Security.AccessControl.AccessControlType]::Allow
    )
    $acl.SetAccessRule($fullControl)
    Set-Acl -LiteralPath $tempDirectory -AclObject $acl

    $fileAcl = Get-Acl -LiteralPath $defaultsFile
    $fileAcl.SetAccessRuleProtection($true, $false)
    $fileRule = [Security.AccessControl.FileSystemAccessRule]::new(
        $currentUser,
        [Security.AccessControl.FileSystemRights]::FullControl,
        [Security.AccessControl.AccessControlType]::Allow
    )
    $fileAcl.SetAccessRule($fileRule)
    Set-Acl -LiteralPath $defaultsFile -AclObject $fileAcl

    $bootstrapSql = @"
CREATE DATABASE IF NOT EXISTS ``$DatabaseName`` CHARACTER SET utf8mb4;
CREATE USER IF NOT EXISTS '$DatabaseUser'@'127.0.0.1' IDENTIFIED BY '$appPassword';
ALTER USER '$DatabaseUser'@'127.0.0.1' IDENTIFIED BY '$appPassword';
GRANT SELECT, INSERT, UPDATE, DELETE ON ``$DatabaseName``.* TO '$DatabaseUser'@'127.0.0.1';
"@
    $bootstrapSql += [Environment]::NewLine + (Get-Content -LiteralPath $schemaPath -Raw)
    [System.IO.File]::WriteAllText(
        $bootstrapFile,
        $bootstrapSql,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "Creating missing tables without deleting existing data..." -ForegroundColor Cyan
    Get-Content -LiteralPath $bootstrapFile -Raw | & $dbClient "--defaults-extra-file=$defaultsFile" --batch
    if ($LASTEXITCODE -ne 0) { throw "Could not create the database or application account. Check the root password and MariaDB log." }

    # CREATE TABLE IF NOT EXISTS does not add columns to an existing installation.
    $migrations = @(
        @{ Table = 'tow'; Column = 'vat_rate'; Definition = 'DECIMAL(5,2) NOT NULL DEFAULT 0' },
        @{ Table = 'wz_p'; Column = 'vat_rate'; Definition = 'DECIMAL(5,2) NOT NULL DEFAULT 0' },
        @{ Table = 'pz_p'; Column = 'vat_rate'; Definition = 'DECIMAL(5,2) NOT NULL DEFAULT 0' },
        @{ Table = 'tow'; Column = 'added_at'; Definition = 'DATETIME NULL' },
        @{ Table = 'tow'; Column = 'modified_at'; Definition = 'DATETIME NULL' },
        @{ Table = 'wz'; Column = 'issue_date'; Definition = 'DATE NULL' },
        @{ Table = 'pz'; Column = 'issue_date'; Definition = 'DATE NULL' }
    )
    foreach ($migration in $migrations) {
        $table = $migration.Table
        $column = $migration.Column
        $columnCheck = "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = '$DatabaseName' AND TABLE_NAME = '$table' AND COLUMN_NAME = '$column';"
        $columnCount = @($columnCheck | & $dbClient "--defaults-extra-file=$defaultsFile" "--database=$DatabaseName" --batch --skip-column-names)
        if ($LASTEXITCODE -ne 0 -or $columnCount.Count -ne 1) {
            throw "Could not check column $column in table $table."
        }
        $columnCountValue = $columnCount[0].Trim()
        if ($columnCountValue -notin @('0', '1')) {
            throw "Unexpected column check result for $table`.$column`: $columnCountValue"
        }
        if ($columnCountValue -eq '0') {
            Write-Host "Adding column $column to $table..." -ForegroundColor Cyan
            "ALTER TABLE ``$table`` ADD COLUMN ``$column`` $($migration.Definition);" |
                & $dbClient "--defaults-extra-file=$defaultsFile" "--database=$DatabaseName" --batch
            if ($LASTEXITCODE -ne 0) { throw "Could not add column $column to table $table." }
        }
    }

    $installedPath = (New-Item -Path $InstallDirectory -ItemType Directory -Force).FullName
    if (-not [string]::Equals($source, $installedPath, [StringComparison]::OrdinalIgnoreCase)) {
        Copy-Item -Path (Join-Path $source "*") -Destination $installedPath -Recurse -Force
    }

    # Keep the repair launcher next to WMS.exe so startup errors can open it.
    $installedInstaller = Join-Path $installedPath "installer"
    New-Item -Path $installedInstaller -ItemType Directory -Force | Out-Null
    foreach ($name in @('Run-Installer.ps1', 'Install-WMS.ps1', 'schema.sql')) {
        $from = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot $name)).Path
        $to = Join-Path $installedInstaller $name
        if (-not [string]::Equals($from, $to, [StringComparison]::OrdinalIgnoreCase)) {
            Copy-Item -LiteralPath $from -Destination $to -Force
        }
    }
    $launcherSource = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\Zainstaluj-WMS.cmd")).Path
    $launcherDestination = Join-Path $installedPath "Zainstaluj-WMS.cmd"
    if (-not [string]::Equals($launcherSource, $launcherDestination, [StringComparison]::OrdinalIgnoreCase)) {
        Copy-Item -LiteralPath $launcherSource -Destination $launcherDestination -Force
    }

    $configDirectory = Join-Path $env:ProgramData "WMS"
    New-Item -Path $configDirectory -ItemType Directory -Force | Out-Null
    $configPath = Join-Path $configDirectory "database.ini"
    @"
[database]
host = 127.0.0.1
port = 3306
name = $DatabaseName
user = $DatabaseUser
password = $appPassword
"@ | Set-Content -LiteralPath $configPath -Encoding UTF8

    try {
        $shortcutPath = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\WMS.lnk"
        $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcutPath)
        $shortcut.TargetPath = Join-Path $InstallDirectory "WMS.exe"
        $shortcut.WorkingDirectory = $InstallDirectory
        $shortcut.Description = "WMS"
        $shortcut.Save()
    }
    catch {
        Write-Warning "Nie udalo sie utworzyc skrotu w menu Start: $_"
    }

    Write-Host "Installation complete. Start: $InstallDirectory\WMS.exe" -ForegroundColor Green
}
finally {
    $rootPassword = $null
    $rootSecure.Dispose()
    Remove-Item -LiteralPath $tempDirectory -Recurse -Force -ErrorAction SilentlyContinue
}
