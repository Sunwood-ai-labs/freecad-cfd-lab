# Download only the upstream archives listed in the experiment's manifest.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'archive-manifest.json') -Raw | ConvertFrom-Json
foreach ($entry in $manifest) {
    if ([IO.Path]::GetFileName($entry.file) -ne $entry.file) { throw 'Manifest filename must be a basename.' }
    $destination = Join-Path $PSScriptRoot $entry.file
    if (Test-Path -LiteralPath $destination) {
        $actual = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $entry.sha256) { throw "Existing file has a different SHA256: $destination" }
        Write-Output "Verified existing $($entry.file)"
        continue
    }
    $partial = $destination + '.partial'
    Invoke-WebRequest -Uri $entry.source_url -OutFile $partial
    $actual = (Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $entry.sha256) { throw "SHA256 mismatch: $($entry.file). The upstream rolling archive may have changed. The .partial file is retained for inspection." }
    if ((Get-Item -LiteralPath $partial).Length -ne $entry.bytes) { throw "Size mismatch: $($entry.file)" }
    Move-Item -LiteralPath $partial -Destination $destination
    Write-Output "Downloaded and verified $($entry.file)"
}
