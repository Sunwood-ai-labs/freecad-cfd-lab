# Build a fresh runtime; this does not replace an existing differently tagged image.
[CmdletBinding()]
param(
    [string]$Image = 'localhost/freecad-cfd-lab:rebuild',
    [string]$WslDistribution = 'podman-machine-default',
    [ValidateRange(1,64)][int]$BuildJobs = 4
)
$ErrorActionPreference = 'Stop'
$entries = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'archive-manifest.json') -Raw | ConvertFrom-Json
foreach ($entry in $entries) {
    $archive = Join-Path $PSScriptRoot $entry.file
    if (-not (Test-Path -LiteralPath $archive)) { throw "Missing $archive. Run Get-Dependencies.ps1 first." }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "SHA256 mismatch: $archive" }
}
if ($WslDistribution) {
    # WSL's launcher can consume backslashes; wslpath also accepts drive paths
    # with forward slashes, including paths containing spaces.
    $windowsContext = $PSScriptRoot.Replace([char]92, [char]47)
    $context = & wsl.exe -d $WslDistribution -u root -- wslpath -a $windowsContext
    if ($LASTEXITCODE -ne 0) { throw 'Unable to translate runtime directory into WSL.' }
    & wsl.exe -d $WslDistribution -u root -- podman build --format docker --build-arg "BUILD_JOBS=$BuildJobs" --tag $Image --file "$context/Containerfile" $context
} else {
    & podman build --format docker --build-arg "BUILD_JOBS=$BuildJobs" --tag $Image --file (Join-Path $PSScriptRoot 'Containerfile') $PSScriptRoot
}
if ($LASTEXITCODE -ne 0) { throw "Runtime build exited $LASTEXITCODE" }
