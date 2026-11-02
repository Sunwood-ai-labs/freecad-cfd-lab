[CmdletBinding()]
param(
    [string]$Image = 'localhost/cfdof-openfoam:verified-20261030',
    [string]$WslDistribution = 'podman-machine-default',
    [string]$OutputDirectory = (Join-Path $PSScriptRoot 'logs')
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
function Invoke-Podman([string[]]$Arguments) {
    if ($WslDistribution) { & wsl.exe -d $WslDistribution -u root -- podman @Arguments }
    else { & podman @Arguments }
    if ($LASTEXITCODE -ne 0) { throw "Podman exited $LASTEXITCODE" }
}
$versions = Invoke-Podman -Arguments @('run','--rm','--network','none','--entrypoint','/bin/bash',$Image,'-c','source /etc/bashrc && cartesianMesh -version && hisa -version && gmsh -version')
$versions | Set-Content -LiteralPath (Join-Path $OutputDirectory 'versions.log') -Encoding utf8
$versionText = $versions -join "`n"
if ($versionText -notmatch 'cfMesh-CfdOF[^\r\n]*\b1\.32\b') { throw 'Expected cfMesh-CfdOF 1.32.' }
if ($versionText -notmatch '(?m)^hisa 1\.13\.4\s*$') { throw 'Expected HiSA 1.13.4.' }
if ($versionText -notmatch '(?m)^4\.15\.2\s*$') { throw 'Expected Gmsh 4.15.2.' }
$helpOutput = Invoke-Podman -Arguments @('run','--rm','--network','none','--entrypoint','/bin/bash',$Image,'-c','source /etc/bashrc && cartesianMesh -help && hisa -help && gmsh -help')
$helpOutput | Set-Content -LiteralPath (Join-Path $OutputDirectory 'help.log') -Encoding utf8
$imageId = Invoke-Podman -Arguments @('image','inspect',$Image,'--format','{{.Id}}')
[ordered]@{
    image=$Image; image_id=($imageId -join '').Trim(); wsl_distribution=$WslDistribution
    openfoam='2306'; cfmesh='1.32'; hisa='1.13.4'; gmsh='4.15.2'
    version_exit_code=0; help_exit_code=0; verified_at=(Get-Date).ToString('o')
    scope='Existing image version/help smoke only; no clean rebuild or CFD rerun.'
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $OutputDirectory 'runtime-verified.json') -Encoding utf8
Get-Content -LiteralPath (Join-Path $OutputDirectory 'runtime-verified.json')
