<#
Copy the published input snapshot beside the release result cases.
This does not start FreeCAD, generate a mesh, or run OpenFOAM.
The 3D 0/U field is intentionally supplied only in the result release ZIP.
#>
param(
    [Parameter(Mandatory)]
    [ValidateSet('elbow', 'window-comparison', 'family-house-airflow')]
    [string]$Experiment
)
$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path $PSScriptRoot -Parent
$experimentRoot = Join-Path (Join-Path $repositoryRoot 'experiments') $Experiment
$roots = if ($Experiment -eq 'window-comparison') {
    @((Join-Path $experimentRoot 'case-a'), (Join-Path $experimentRoot 'case-b'))
} else { @($experimentRoot) }
foreach ($root in $roots) {
    $snapshot = Join-Path $root 'input'
    foreach ($part in @('case', 'meshCase')) {
        $source = Join-Path $snapshot $part
        $destination = Join-Path $root $part
        if (-not (Test-Path -LiteralPath $source -PathType Container)) {
            throw "Input snapshot not found: $source"
        }
        New-Item -ItemType Directory -Path $destination -Force | Out-Null
        Get-ChildItem -LiteralPath $source -Force | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $destination -Recurse -Force
        }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $root 'case/0/U'))) {
        throw "Extract the final result release ZIP first; exact initial field missing at $root/case/0/U"
    }
    Write-Output "Prepared input directories: $root"
}
