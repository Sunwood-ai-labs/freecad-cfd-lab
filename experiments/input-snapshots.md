# OpenFOAM input snapshots

Each CFD experiment has an `input/case` and `input/meshCase` snapshot (inside
`case-a` / `case-b` for the two-window comparison). These are the actual saved
OpenFOAM dictionaries and geometry from the experiment. Generated meshes and
computed result fields are distributed as release ZIPs instead of Git objects.

The 31 MB `family-house-airflow/input/case/0/U` field is omitted: it contains
538,479 potential-flow-initialized vectors. Its exact original is included as
`family-house-airflow/case/0/U` in the final result release. No replacement
initial field was invented for publication.

After extracting the release ZIP at the repository root, prepare the input
directories for the saved execution scripts:

```powershell
.\scripts\Prepare-CfdInputs.ps1 -Experiment family-house-airflow
```

Use `elbow` or `window-comparison` for the other cases. This copies the input
snapshot beside the result case. It does not calculate CFD. A subsequent CFD
rerun replaces result files and logs; use a separate checkout or backup first.

Python and FreeCAD macros under `source/` have been adapted to this repository
layout. `adapter-final.json` now resolves paths relative to the experiment
directory. `Run-OpenFOAM.ps1` accepts `-WslDistribution` and `-ContainerImage`.
The default image name refers to the original locally built image, not a public
container registry. Build instructions are in the top-level documentation and
the saved `elbow/runtime/Containerfile`.

These relocated scripts pass syntax checks. Their full build / CFD rerun on a
fresh machine has **not** been performed. Original observation JSON and logs
retain their historical absolute paths and checksums. Do not interpret them as
evidence of a new run from this checkout. The Japanese `.txt` files are original
dated experiment notes; top-level documentation describes the published layout
and the later 3D experiment that supersedes the BIM note's “CFD not run” status.

`source-manifest.json` maps every copied artifact to its original relative path
and records both original and published SHA-256 hashes. Changes to executable
paths and the renderer adapter are identified by `adapted: true`.
