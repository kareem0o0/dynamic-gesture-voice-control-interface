<#
PowerShell build script for Windows using PyInstaller.
Run from repository root in an elevated PowerShell prompt or developer shell.

Usage:
  ./scripts/build_windows.ps1

This script assumes Python and PyInstaller are available in PATH (or in a venv you activate).
#>

param()

Set-StrictMode -Version Latest

$AppName = "SuperClawBot"
$Entry = "main.py"

Write-Host "Building $AppName (entry: $Entry) for Windows..."

function Add-DataArg($path) {
    # On Windows, PyInstaller uses src;dest for --add-data
    return "--add-data `"$path;$path`""
}

$folders = @('resources','models','model_mappings','saved_configurations','ui','controllers','core','utils')
$addDataArgs = @()
foreach ($f in $folders) {
    if (Test-Path $f) {
        $addDataArgs += (Add-DataArg $f)
    }
}

# Exclude other Qt bindings if present - target is PySide6
$excludeArgs = @('--exclude-module','PyQt5','--exclude-module','PySide2')

# Build command
$cmd = @('pyinstaller','--noconfirm','--clean','--onedir','--name',$AppName) + $excludeArgs + $addDataArgs + @($Entry)

Write-Host "Running:" ($cmd -join ' ')

& pyinstaller --noconfirm --clean --onedir --name $AppName @($excludeArgs) @($addDataArgs) $Entry

Write-Host "Build finished. See dist\$AppName for output (or App\$AppName if you rename)."
