# Reproduction / 再現手順

Run these commands in **Windows PowerShell**, from the cloned repository root.
Use `uv` for Python helpers. Rendering requires ParaView's own `pvpython.exe`,
which supplies its ParaView/VTK Python modules; an ordinary Python environment
cannot substitute for that interpreter.

## 1. Browse the saved experiment

Images, WebP previews, MP4 videos, JSON summaries and `.FCStd` models are included
in Git. Opening the existing media does not require OpenFOAM. Open `.FCStd` in
FreeCAD to inspect the design or the CFD setup.

## 2. Download final CFD fields

```powershell
New-Item -ItemType Directory -Force downloads | Out-Null
gh release download experiment-data-v1 --repo Sunwood-ai-labs/freecad-cfd-lab --pattern '*.zip' --pattern 'SHA256SUMS.txt' --pattern 'release-manifest.json' --dir downloads

Get-Content downloads/SHA256SUMS.txt | ForEach-Object {
    $hash, $name = $_ -split '\s+', 2
    $actual = (Get-FileHash -LiteralPath (Join-Path downloads $name.Trim()) -Algorithm SHA256).Hash
    if ($actual.ToLowerInvariant() -ne $hash.ToLowerInvariant()) { throw "Hash mismatch: $name" }
    Write-Output "OK: $name"
}

Expand-Archive -LiteralPath downloads/family-house-airflow-results.zip -DestinationPath .
```

Only extract the needed archive. The ZIP layout is already rooted at
`experiments/`. Extraction into a fresh clone adds case folders; avoid overwriting
a case you have since modified. The release contains:

| Archive | Destination | Final iteration |
| --- | --- | --- |
| `elbow-results.zip` | `experiments/elbow/case/` | 242 |
| `window-comparison-results.zip` | `experiments/window-comparison/case-a/case/` and `case-b/case/` | 1429 / 2026 |
| `family-house-airflow-results.zip` | `experiments/family-house-airflow/case/` | 697 |

Each has `0`, `constant/polyMesh`, `system`, the final field and a `pv.foam`
marker. Archived source headers may retain historical locations. Those headers
do not require that original path on the current machine.

## 3. View in ParaView

Open `experiments/family-house-airflow/case/pv.foam` in ParaView. Apply the reader,
select the latest time, choose velocity `U`, and use a slice or stream tracer.
The archived final iteration is a steady solver iteration, not 697 seconds of a
physical transient. For the other experiments, open their respective `pv.foam`.

## 4. Render the house animation again

Install the recorded compatible environment from [environment.md](environment.md),
including ParaView, FFmpeg and the renderer's Python dependencies. The original
renderer uses Windows Yu Gothic fonts, which are not bundled.

```powershell
$pvpython = Read-Host 'Absolute path to ParaView bin/pvpython.exe'
uv run -- $pvpython experiments/family-house-airflow/source/render_family_airflow.py --root experiments/family-house-airflow --work replay/family-house --design experiments/family-house-airflow/source-design.json --adapter experiments/family-house-airflow/source/adapter-final.json
```

Public sources have path adaptations for the repository layout. The existing
animation was decoded and visually checked during the original experiment;
the adapted public renderer has not been run end to end on a new machine.
Rendering can rewrite media and metric files under `--root`; make a working copy
if you want to preserve the packaged evidence exactly.

## 5. Recalculate or change the model

Read each experiment's source, original notes and saved input dictionaries first.
`runtime/` provides the container build recipe and checksum-verified upstream
downloads. Do not replace your FreeCAD preferences with archived paths.

For the house, the original flow was: generate a derived FreeCAD/CfdOF model,
mesh it, initialize, solve in eight processes, adjust relaxation/numerics,
continue with stricter residual criteria, reconstruct, independently audit fields
and fluxes, then render. The source folder preserves these stages.

The archived `case/0/U` is the exact nonuniform initialized field and is supplied
in the release rather than Git. An input-dictionary snapshot alone is not the
complete initial case. Start from the release case in a separate working copy.
Use the meshing inputs when intentionally remeshing; copy neither the final
697 field nor intermediate fields into `0` as an unrecorded shortcut.

**Recalculation is an experimental workflow, not a verified one-command installer.**
The final wrapper was not rerun in full, GUI case re-export may replace manual
overrides, and the initial builder does not encode every later continuation
choice. Changing the mesh or conditions invalidates the original validation
records. Keep new results and checks separate from the historical evidence.

The release omits intermediate 500/585 fields and processor directories. The
saved stability reports are available, but rerunning those exact historical
comparisons requires the original intermediate data or a newly recorded solve.

## 6. Repository checks

```powershell
uv run scripts/verify_artifacts.py
uv run scripts/verify_repository.py
```

The validation workflow checks packaged JSON, source syntax, local Markdown
links, model archives, evidence invariants and payload exclusions. It does not
execute FreeCAD or solve CFD. See the workflow for the exact validation command
and [QA inventory](qa-inventory.md) for publication scope.
