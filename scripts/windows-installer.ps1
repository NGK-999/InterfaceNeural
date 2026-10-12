#Requires -Version 7.0
# Build e teste em Windows; o compilador fica isolado na pasta temporaria.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:GITHUB_ACTIONS -ne 'true' -or [string]::IsNullOrWhiteSpace($env:RUNNER_TEMP)) {
    throw 'Este teste de instalacao/desinstalacao so pode rodar na CI do GitHub.'
}

function Invoke-CheckedProcess {
    param([string]$FilePath, [string[]]$Arguments)
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "Processo falhou: $FilePath (saida $($process.ExitCode))"
    }
}

$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    $bundle = Join-Path $projectRoot 'dist\MuscleMonitor'
    if (-not (Test-Path (Join-Path $bundle 'MuscleMonitor.exe'))) {
        throw 'Gere o pacote Windows com python scripts/build.py primeiro.'
    }
    $temporaryRoot = $env:RUNNER_TEMP
    $toolRoot = Join-Path $temporaryRoot 'inno-setup-6.7.3'
    $compiler = Join-Path $toolRoot 'ISCC.exe'
    if (-not (Test-Path $compiler)) {
        $download = Join-Path $temporaryRoot 'innosetup-6.7.3.exe'
        $url = 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe'
        $expectedHash = '9c73c3bae7ed48d44112a0f48e66742c00090bdb5bef71d9d3c056c66e97b732'
        Invoke-WebRequest -Uri $url -OutFile $download
        if ((Get-FileHash $download -Algorithm SHA256).Hash -ne $expectedHash) {
            throw 'Download do compilador com SHA256 diferente do esperado.'
        }
        $signature = Get-AuthenticodeSignature $download
        if ($signature.Status -ne 'Valid' -or
            $signature.SignerCertificate.Subject -notmatch 'CN=Pyrsys B\.V\.(,|$)') {
            throw 'Assinatura do compilador nao corresponde ao fornecedor verificado.'
        }
        Invoke-CheckedProcess $download @(
            '/CURRENTUSER', '/PORTABLE=1', '/VERYSILENT', '/SUPPRESSMSGBOXES',
            '/NORESTART', '/SP-', "/DIR=`"$toolRoot`""
        )
    }
    if (-not (Test-Path $compiler)) {
        throw 'O compilador Inno Setup nao foi encontrado apos a preparacao.'
    }
    # ISCC.exe tem FileVersion 0.0.0.0 no recurso oficial. A receita verifica
    # PREPROCVER (SetupBinVersion) antes de compilar, sem interpretar esse texto.
    $license = Join-Path $toolRoot 'license.txt'
    if (-not (Test-Path $license)) { throw 'Licenca do Inno Setup ausente.' }
    Copy-Item $license (Join-Path $bundle '_internal\licenses\INNO-SETUP.txt')
    $version = (python -c 'from muscle_monitor import __version__; print(__version__)').Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel ler a versao do aplicativo.' }
    & $compiler "/DAppVersion=$version" 'packaging\windows.iss'
    if ($LASTEXITCODE -ne 0) { throw 'Compilacao do instalador falhou.' }

    $installer = Join-Path $projectRoot 'dist\installer\MonitorMuscular-Instalar.exe'
    if (-not (Test-Path $installer)) { throw 'Instalador nao foi gerado.' }
    $evidence = Join-Path $projectRoot 'artifacts'
    New-Item -ItemType Directory -Force $evidence | Out-Null
    $target = Join-Path $temporaryRoot 'Monitor com espaço e ação'
    if (Test-Path $target) { throw 'Pasta de teste ja existe; preservada sem alteracoes.' }
    $desktop = [Environment]::GetFolderPath('Desktop')
    $shortcut = Join-Path $desktop 'Monitor de Sinais Musculares.lnk'
    if (Test-Path $shortcut) { throw 'Atalho ja existe; preservado sem alteracoes.' }
    $programs = [Environment]::GetFolderPath('Programs')
    $menuShortcut = Join-Path $programs 'Monitor de Sinais Musculares.lnk'
    $registry = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\MuscleMonitorV1_is1'
    if ((Test-Path $registry) -or (Test-Path $menuShortcut)) {
        throw 'Instalacao/atalho anterior encontrado; preservado sem alteracoes.'
    }

    Invoke-CheckedProcess $installer @(
        '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
        '/RESTARTEXITCODE=3010', "/DIR=`"$target`"",
        "/LOG=`"$(Join-Path $evidence 'installer-install.log')`""
    )
    try {
        # Confere o payload inteiro, inclusive DLLs/licencas; sem dados da placa.
        foreach ($file in Get-ChildItem $bundle -Recurse -File) {
            $relative = [IO.Path]::GetRelativePath($bundle, $file.FullName)
            $installed = Join-Path $target $relative
            if (-not (Test-Path $installed) -or
                (Get-FileHash $file.FullName).Hash -ne (Get-FileHash $installed).Hash) {
                throw "Arquivo instalado ausente ou diferente: $relative"
            }
        }
        if (-not (Test-Path $shortcut)) { throw 'Atalho da area de trabalho nao foi criado.' }
        $shell = New-Object -ComObject WScript.Shell
        $link = $shell.CreateShortcut($shortcut)
        if ($link.TargetPath -ne (Join-Path $target 'MuscleMonitor.exe')) {
            throw 'Atalho aponta para um executavel diferente do instalado.'
        }
        if ($link.WorkingDirectory -ne $target) {
            throw 'Atalho nao usa a pasta do aplicativo como diretorio de trabalho.'
        }
        Invoke-CheckedProcess (Join-Path $target 'MuscleMonitor.exe') @('--smoke-test')
    }
    finally {
        $uninstaller = Join-Path $target 'unins000.exe'
        if (Test-Path $uninstaller) {
            Invoke-CheckedProcess $uninstaller @(
                '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                "/LOG=`"$(Join-Path $evidence 'installer-uninstall.log')`""
            )
        }
    }
    if ((Test-Path (Join-Path $target 'MuscleMonitor.exe')) -or (Test-Path $shortcut) -or
        (Test-Path $menuShortcut) -or (Test-Path $registry)) {
        throw 'Desinstalacao deixou executavel, atalho ou registro.'
    }
    Write-Host 'Instalador, payload, atalho, simulacao e desinstalacao verificados.'
}
finally {
    Pop-Location
}
