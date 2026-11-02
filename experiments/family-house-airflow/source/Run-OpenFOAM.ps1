param(
    [string]$WslDistribution = 'podman-machine-default',
    [string]$ContainerImage = 'localhost/cfdof-openfoam:verified-20261030'
)
# Re-run the supplied mesh/case. This replaces CFD result folders and logs.
# Original Family-House BIM/design and saved CfdOF settings are not modified.
$ErrorActionPreference = 'Stop'
$analysisRoot = Split-Path $PSScriptRoot -Parent
if ((Split-Path $PSScriptRoot -Leaf) -ne 'source') {
    throw 'Run the delivered copy under experiments/family-house-airflow/source.'
}
if (-not (Test-Path -LiteralPath (Join-Path $analysisRoot 'case/system/controlDict'))) {
    throw 'The supplied OpenFOAM case was not found.'
}
$analysisLinux = '/mnt/' + $analysisRoot.Substring(0,1).ToLower() + $analysisRoot.Substring(2).Replace('\','/')
$sourceLinux = $analysisLinux + '/source'
& uv run -- python (Join-Path $PSScriptRoot 'reset_initial_relaxation.py')
if ($LASTEXITCODE -ne 0) { throw 'Unable to reset initial relaxation.' }
[System.IO.File]::WriteAllText((Join-Path $analysisRoot 'solver-run.log'),'')
$controllerScript = '"' + (Join-Path $PSScriptRoot 'tune_relaxation.py') + '"'
$controller = Start-Process -FilePath (Get-Command uv).Source -ArgumentList @('run','--','python',$controllerScript) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $analysisRoot 'relaxation-controller.log') -RedirectStandardError (Join-Path $analysisRoot 'relaxation-controller.err')
try {
    & wsl.exe -d $WslDistribution -u root -- podman run --rm --network none --log-driver k8s-file --entrypoint /bin/bash -v "${analysisLinux}:/tmp" -v "${sourceLinux}:/scripts:ro" $ContainerImage /scripts/run_cfd.sh
    if ($LASTEXITCODE -ne 0) { throw "OpenFOAM exited with $LASTEXITCODE; inspect mesh/solver logs." }
} finally {
    if (-not $controller.HasExited) { Stop-Process -Id $controller.Id }
}
& uv run --with numpy -- python (Join-Path $PSScriptRoot 'validate_solution.py')
if ($LASTEXITCODE -ne 0) { throw 'Numerical validation failed.' }
