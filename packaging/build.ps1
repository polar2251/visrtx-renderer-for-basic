param(
    [string]$Python = 'python',
    [string]$InnoCompiler = 'ISCC.exe',
    [string]$Version = '0.1.0'
)

$ErrorActionPreference = 'Stop'
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Expected a version in major.minor.patch format."
}
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $notices = (Resolve-Path -LiteralPath 'THIRD-PARTY.md').Path
    & $Python -m PyInstaller --noconfirm --clean --onedir --windowed --noupx `
        --name VisrtxRendererForBasic --additional-hooks-dir $PSScriptRoot --specpath build `
        --add-data "$($notices):." app.py
    if ($LASTEXITCODE) { throw "PyInstaller exited with $LASTEXITCODE." }

    # Qt uses Windows' ICU exports. PyInstaller can also discover unrelated ICU DLLs on PATH.
    foreach ($library in 'icuuc.dll', 'icuin.dll', 'icudt.dll') {
        $bundled = "dist/VisrtxRendererForBasic/_internal/$library"
        if (Test-Path -LiteralPath $bundled) { Remove-Item -LiteralPath $bundled }
    }

    & $Python packaging/smoke.py dist/VisrtxRendererForBasic/VisrtxRendererForBasic.exe
    if ($LASTEXITCODE) { throw "Packaged render smoke test failed." }

    & $InnoCompiler "/DAppVersion=$Version" packaging/installer.iss
    if ($LASTEXITCODE) { throw "Inno Setup exited with $LASTEXITCODE." }

    $installer = 'dist/VisrtxRendererForBasic-Setup-x64.exe'
    $hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  $(Split-Path -Leaf $installer)" | Set-Content -LiteralPath "$installer.sha256" -Encoding ASCII
} finally {
    Pop-Location
}
