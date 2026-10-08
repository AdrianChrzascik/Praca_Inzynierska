$ErrorActionPreference = "Stop"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdministrator)) {
    try {
        $powershell = Join-Path $PSHOME "powershell.exe"
        $arguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ('"{0}"' -f $PSCommandPath))
        $process = Start-Process -FilePath $powershell -ArgumentList $arguments -Verb RunAs -Wait -PassThru
        exit $process.ExitCode
    }
    catch {
        Write-Host "Nie udalo sie uruchomic instalatora z uprawnieniami administratora: $_" -ForegroundColor Red
        Read-Host "Nacisnij Enter, aby zamknac okno"
        exit 1
    }
}

try {
    & (Join-Path $PSScriptRoot "Install-WMS.ps1")
    Write-Host "Instalacja WMS zakonczona." -ForegroundColor Green
    Read-Host "Nacisnij Enter, aby zamknac okno"
    exit 0
}
catch {
    Write-Host "Instalacja nie powiodla sie: $_" -ForegroundColor Red
    Read-Host "Nacisnij Enter, aby zamknac okno"
    exit 1
}
